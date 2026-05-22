"""LAN server. One TCP listener; each accepted connection runs its own
isolated game session on its own OS thread.

Design notes:
- Thread-per-connection (`socketserver.ThreadingTCPServer`). Avoids the
  ~3,500-line async refactor an asyncio rewrite would require. The GIL is a
  non-issue: the workload is purely IO-bound.
- One session per player_name at a time (enforced via the server's claim_name
  lock). Required because `auto.json` and `achievements.json` are not designed
  for concurrent writers.
- Per-connection idle timeout (default 30 min). On timeout, NetIO returns
  "quit", the session autosaves, and we disconnect.
- LAN-only by design: no auth, no TLS. Document this; don't port-forward it.
"""

import socketserver
import threading
from typing import Optional

from .name_registry import NameRegistry


DEFAULT_PORT = 4404
DEFAULT_MAX_SESSIONS = 8
DEFAULT_IDLE_TIMEOUT_SECONDS = 1800   # 30 minutes


class BSGRequestHandler(socketserver.StreamRequestHandler):
    """One per accepted connection. Runs the full per-session lifecycle:
    title → name prompt → session loop → NG+ loop → disconnect."""

    timeout = DEFAULT_IDLE_TIMEOUT_SECONDS

    def setup(self) -> None:
        super().setup()
        # Apply the class-level timeout to the underlying socket so readline()
        # in NetIO raises socket.timeout after `timeout` seconds of inactivity.
        if self.timeout is not None:
            self.request.settimeout(self.timeout)

    def handle(self) -> None:
        from engine.io import NetIO
        from engine.session import Session
        # main.py owns the title/name-prompt UX; we reuse it verbatim.
        from main import show_title, prompt_for_name, build_world

        io = NetIO(self.rfile, self.wfile)
        peer = self.client_address
        log = self.server.log

        log(f"[connect] {peer}")
        try:
            show_title(io)
            name = prompt_for_name(io)
        except Exception as exc:
            log(f"[disconnect-on-greeting] {peer}: {exc!r}")
            return

        claimed = self.server.claim_name(name)
        if not claimed:
            io.send(self.server.refusal_message(name))
            log(f"[refuse] {peer} wanted '{name}'")
            return

        log(f"[session-start] {peer} as '{name}'")
        try:
            io.send(
                f"\nINTERCOM: ACKNOWLEDGED, SPECIALIST {name.upper()}. "
                "WELCOME TO ANOTHER FRAKKIN' SHIFT.\n"
            )
            self._run_session_with_ng_plus(io, name, build_world)
        except Exception as exc:
            log(f"[session-error] {peer} '{name}': {exc!r}")
        finally:
            self.server.release_name(name)
            log(f"[disconnect] {peer} '{name}'")

    def _run_session_with_ng_plus(self, io, name: str, build_world) -> None:
        from engine.session import Session

        log = self.server.log

        ng_plus_context = None
        while True:
            if ng_plus_context and ng_plus_context.get("ng_plus"):
                io.send("")
                io.send(
                    "── ALL OF THIS HAS HAPPENED BEFORE ──\n\n"
                    "You wake up. Again. The intercom is the same. The bunk is the same.\n"
                    "Hadrian is the same. The dent without a story is, you swear, in a\n"
                    "different place than you remembered. You shake it off. Mostly."
                )
                io.send("")
            world = build_world(name, ng_plus_context)
            # Inject the server's log function so ending-finalize failures
            # surface in journald instead of vanishing.
            session = Session(io=io, world=world, log_fn=log)
            next_action = session.run()
            if not next_action or not next_action.get("ng_plus"):
                return
            ng_plus_context = next_action


class BSGServer(socketserver.ThreadingTCPServer):
    """ThreadingTCPServer with a name-claim registry and configurable caps.

    The name registry can be SHARED with another listener (e.g. the HTTP
    server) by passing an existing NameRegistry into the constructor. This
    keeps the TCP-vs-browser name-collision semantics correct when one
    process runs both transports."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        max_sessions: int = DEFAULT_MAX_SESSIONS,
        idle_timeout: int = DEFAULT_IDLE_TIMEOUT_SECONDS,
        log_fn=None,
        name_registry: Optional[NameRegistry] = None,
    ) -> None:
        # Class-level timeout on the handler. Mutating this is the documented
        # way to set it; the handler reads it in setup().
        BSGRequestHandler.timeout = idle_timeout
        super().__init__(server_address, BSGRequestHandler)
        self.max_sessions = max_sessions
        self._registry = name_registry or NameRegistry(max_sessions)
        self._log_fn = log_fn or (lambda msg: print(msg, flush=True))

    def log(self, msg: str) -> None:
        self._log_fn(msg)

    def claim_name(self, name: str) -> bool:
        return self._registry.claim(name)

    def release_name(self, name: str) -> None:
        self._registry.release(name)

    def refusal_message(self, name: str) -> str:
        return self._registry.refusal_message(name)

    @property
    def active_count(self) -> int:
        return self._registry.active_count


def serve_forever(
    bind_addr: str = "0.0.0.0",
    port: int = DEFAULT_PORT,
    max_sessions: int = DEFAULT_MAX_SESSIONS,
    idle_timeout: int = DEFAULT_IDLE_TIMEOUT_SECONDS,
    log_fn=None,
    name_registry: Optional[NameRegistry] = None,
) -> None:
    """Block forever serving the BSG Adventure LAN TCP server.

    Imports content eagerly so the first connection doesn't pay the registration
    cost (and so two simultaneous early connections can't race the import lock)."""
    import content  # noqa: F401  — triggers all content registration

    server = BSGServer(
        (bind_addr, port),
        max_sessions=max_sessions,
        idle_timeout=idle_timeout,
        log_fn=log_fn,
        name_registry=name_registry,
    )
    server.log(
        f"BSG Adventure (TCP) listening on {bind_addr}:{port} "
        f"(max {max_sessions} sessions, idle timeout {idle_timeout}s)"
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()
