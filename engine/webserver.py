"""LAN HTTP listener for browser play.

The browser connects to this server and runs the same per-session game loop
as a telnet client — only the IO adapter differs. Transport protocol:

  GET  /              → the single-page terminal UI (HTML)
  GET  /style.css     → CSS for the UI
  GET  /app.js        → JS for the UI
  POST /spawn         → create a new session; returns {session_id}
  GET  /events?session=<id>
                      → Server-Sent Events stream of text chunks for that
                        session. Long-lived; keeps writing until the
                        session ends or the browser disconnects.
  POST /input?session=<id>
                      → submit one line of input. Body: raw text. Returns 204.
  POST /close?session=<id>
                      → graceful teardown signal from the browser
                        (sendBeacon on tab close). Returns 204.

LAN-only: same security stance as the TCP listener — no auth, no TLS,
intentionally do not expose to the public internet.

Stdlib only: `http.server.ThreadingHTTPServer` + `socketserver.ThreadingMixIn`,
no pip deps. Each HTTP request is one thread; the long-running SSE stream
holds that thread for the life of the session. The Session loop itself
runs in a separate thread spawned at /spawn time."""

import json
import os
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

from .io import Disconnected, WebIO
from .name_registry import NameRegistry


DEFAULT_PORT = 4405
DEFAULT_IDLE_TIMEOUT_SECONDS = 1800   # 30 min — matches the TCP listener
DEFAULT_GRACE_AFTER_DISCONNECT = 60   # keep a session alive this long after
                                      # the SSE drops, so a browser refresh
                                      # can reattach.
_KEEPALIVE_INTERVAL = 15              # seconds between SSE keepalive comments
_SSE_SEND_TIMEOUT = 1.0               # seconds drain_send blocks before
                                      # writing a keepalive


# Where the static assets live. Resolved relative to the repo root, NOT
# the CWD — the server must work no matter where it's launched from.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_WEB_ROOT = _REPO_ROOT / "web"


# ─── per-browser-session record ──────────────────────────────────────────────


class WebSession:
    """One browser tab. Owns its WebIO, the Session-loop thread, and
    bookkeeping for idle GC."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.io = WebIO()
        self.thread: Optional[threading.Thread] = None
        self.created_at = time.time()
        self.last_activity = self.created_at
        # Set when an SSE writer is currently attached. If False, the
        # session is in a "grace period" — game thread still running but
        # nothing is draining its output queue.
        self.sse_attached = False
        self.detached_at: Optional[float] = None

    def touch(self) -> None:
        self.last_activity = time.time()

    def attach_sse(self) -> None:
        self.sse_attached = True
        self.detached_at = None
        self.touch()

    def detach_sse(self) -> None:
        self.sse_attached = False
        self.detached_at = time.time()

    def is_alive(self) -> bool:
        return self.thread is not None and self.thread.is_alive()


# ─── registry of live web sessions ──────────────────────────────────────────


class WebSessionRegistry:
    def __init__(
        self,
        idle_timeout: int = DEFAULT_IDLE_TIMEOUT_SECONDS,
        grace_after_disconnect: int = DEFAULT_GRACE_AFTER_DISCONNECT,
    ) -> None:
        self._sessions: dict[str, WebSession] = {}
        self._lock = threading.Lock()
        self.idle_timeout = idle_timeout
        self.grace_after_disconnect = grace_after_disconnect

    def create(self) -> WebSession:
        # 16 bytes → 32 hex chars; cryptographically random so the id can't
        # be guessed by another browser on the LAN. The id is the only
        # session credential.
        sid = secrets.token_hex(16)
        ws = WebSession(sid)
        with self._lock:
            self._sessions[sid] = ws
        return ws

    def get(self, session_id: str) -> Optional[WebSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def remove(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def all(self) -> list[WebSession]:
        with self._lock:
            return list(self._sessions.values())

    def gc_once(self, now: Optional[float] = None) -> list[WebSession]:
        """Tear down sessions whose game thread has exited or that have
        been idle past the configured cutoffs. Returns the sessions that
        were reaped (so the caller can log them)."""
        now = now if now is not None else time.time()
        reaped: list[WebSession] = []
        with self._lock:
            for sid, ws in list(self._sessions.items()):
                idle = now - ws.last_activity
                if not ws.is_alive():
                    # Game thread finished — session is over.
                    reaped.append(ws)
                    del self._sessions[sid]
                elif idle > self.idle_timeout:
                    reaped.append(ws)
                    del self._sessions[sid]
                elif (
                    not ws.sse_attached
                    and ws.detached_at is not None
                    and (now - ws.detached_at) > self.grace_after_disconnect
                ):
                    reaped.append(ws)
                    del self._sessions[sid]
        for ws in reaped:
            ws.io.close()
        return reaped


# ─── HTTP handler ────────────────────────────────────────────────────────────


class _Handler(BaseHTTPRequestHandler):
    """All routes for the browser UI. The actual server (BSGWebServer) is
    below; this class is a stateless dispatcher that reads `self.server`
    for the registry / name-claim / log function."""

    # Suppress the noisy default BaseHTTPRequestHandler stderr logging;
    # we route everything through self.server.log() instead.
    def log_message(self, fmt: str, *args) -> None:
        try:
            self.server.log(  # type: ignore[attr-defined]
                f"[http] {self.client_address[0]} {fmt % args}"
            )
        except Exception:
            pass

    # ─── routing ─────────────────────────────────────────────────────────────

    def do_GET(self) -> None:
        u = urlparse(self.path)
        if u.path == "/":
            return self._serve_file("index.html", "text/html; charset=utf-8")
        if u.path == "/style.css":
            return self._serve_file("style.css", "text/css; charset=utf-8")
        if u.path == "/app.js":
            return self._serve_file("app.js", "application/javascript; charset=utf-8")
        if u.path == "/healthz":
            return self._json(200, {"ok": True})
        if u.path == "/events":
            return self._handle_events(u)
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        u = urlparse(self.path)
        if u.path == "/spawn":
            return self._handle_spawn()
        if u.path == "/input":
            return self._handle_input(u)
        if u.path == "/close":
            return self._handle_close(u)
        self._json(404, {"error": "not found"})

    # ─── helpers ─────────────────────────────────────────────────────────────

    def _serve_file(self, relpath: str, content_type: str) -> None:
        p = _WEB_ROOT / relpath
        try:
            data = p.read_bytes()
        except FileNotFoundError:
            return self._json(404, {"error": f"missing: {relpath}"})
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        # Belt-and-braces: tell intermediaries we're serving local-only
        # content with no cache poisoning concerns.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _query(self, u) -> dict:
        return {k: v[0] for k, v in parse_qs(u.query).items() if v}

    def _registry(self) -> WebSessionRegistry:
        return self.server.web_registry  # type: ignore[attr-defined]

    def _name_registry(self) -> NameRegistry:
        return self.server.name_registry  # type: ignore[attr-defined]

    def _log(self, msg: str) -> None:
        try:
            self.server.log(msg)  # type: ignore[attr-defined]
        except Exception:
            pass

    # ─── route handlers ──────────────────────────────────────────────────────

    def _handle_spawn(self) -> None:
        # No body parsing needed — the player name is collected via the
        # in-game prompt over the SSE stream, same as TCP.
        ws = self._registry().create()
        self._start_session_thread(ws)
        self._log(f"[web-spawn] session={ws.session_id[:8]}…")
        self._json(200, {"session_id": ws.session_id})

    def _handle_input(self, u) -> None:
        q = self._query(u)
        sid = q.get("session")
        if not sid:
            return self._json(400, {"error": "missing session"})
        ws = self._registry().get(sid)
        if ws is None:
            return self._json(404, {"error": "no such session"})
        length = int(self.headers.get("Content-Length") or 0)
        # Cap body size so a misbehaving client can't pin RAM.
        if length > 8192:
            return self._json(413, {"error": "input too large"})
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        line = body.rstrip("\r\n")
        ws.touch()
        ws.io.push_input(line)
        # 204 No Content — the response to the player comes via SSE, not
        # this POST's body.
        self.send_response(204)
        self.end_headers()

    def _handle_close(self, u) -> None:
        q = self._query(u)
        sid = q.get("session")
        if not sid:
            return self._json(400, {"error": "missing session"})
        ws = self._registry().get(sid)
        if ws is not None:
            ws.io.close()
            self._log(f"[web-close] session={sid[:8]}…")
        self.send_response(204)
        self.end_headers()

    def _handle_events(self, u) -> None:
        q = self._query(u)
        sid = q.get("session")
        if not sid:
            return self._json(400, {"error": "missing session"})
        ws = self._registry().get(sid)
        if ws is None:
            return self._json(404, {"error": "no such session"})
        # Open the SSE response.
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        # Disable proxy buffering (works for nginx — harmless if absent).
        self.send_header("X-Accel-Buffering", "no")
        # Tell the client to retry after a brief pause if the stream drops.
        # (3000 ms is the EventSource default; explicit for clarity.)
        self.end_headers()
        try:
            self.wfile.write(b"retry: 3000\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return
        ws.attach_sse()
        last_keepalive = time.time()
        try:
            while True:
                if ws.io.closed and ws.io._send_q.empty():
                    break
                chunk = ws.io.drain_send(timeout=_SSE_SEND_TIMEOUT)
                ws.touch()
                if chunk is None:
                    # Keepalive comment every _KEEPALIVE_INTERVAL seconds.
                    now = time.time()
                    if now - last_keepalive >= _KEEPALIVE_INTERVAL:
                        try:
                            self.wfile.write(b": keepalive\n\n")
                            self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError):
                            break
                        last_keepalive = now
                    continue
                payload = json.dumps({"text": chunk})
                try:
                    self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    break
                last_keepalive = time.time()
            # Game thread finished — tell the browser cleanly.
            try:
                self.wfile.write(b"event: end\ndata: {}\n\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
        finally:
            ws.detach_sse()

    # ─── session-loop spawner ────────────────────────────────────────────────

    def _start_session_thread(self, ws: WebSession) -> None:
        log_fn = self._log
        name_registry = self._name_registry()

        def runner() -> None:
            # Lazy import; play_one_player owns the title/name/NG+ loop and
            # is shared with the TCP and local transports.
            from main import play_one_player
            try:
                play_one_player(ws.io, name_registry=name_registry, log_fn=log_fn)
            except Disconnected:
                pass
            except Exception as exc:
                log_fn(f"[web-session-error] {ws.session_id[:8]}… {exc!r}")
            finally:
                # Make sure the SSE writer wakes up and emits the end event.
                ws.io.close()

        t = threading.Thread(
            target=runner, name=f"bsg-web-{ws.session_id[:8]}", daemon=True
        )
        ws.thread = t
        t.start()


# ─── server class ───────────────────────────────────────────────────────────


class BSGWebServer(ThreadingHTTPServer):
    """HTTP listener with a shared NameRegistry and a WebSessionRegistry.
    The reaper thread runs as a daemon and tears down stale sessions."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        name_registry: NameRegistry,
        idle_timeout: int = DEFAULT_IDLE_TIMEOUT_SECONDS,
        grace_after_disconnect: int = DEFAULT_GRACE_AFTER_DISCONNECT,
        log_fn=None,
    ) -> None:
        super().__init__(server_address, _Handler)
        self.name_registry = name_registry
        self.web_registry = WebSessionRegistry(
            idle_timeout=idle_timeout,
            grace_after_disconnect=grace_after_disconnect,
        )
        self._log_fn = log_fn or (lambda msg: print(msg, flush=True))
        # Sweep idle sessions and dead threads periodically.
        self._stop_reaper = threading.Event()
        self._reaper = threading.Thread(
            target=self._reaper_loop, name="bsg-web-reaper", daemon=True
        )
        self._reaper.start()

    def log(self, msg: str) -> None:
        self._log_fn(msg)

    def server_close(self) -> None:
        self._stop_reaper.set()
        super().server_close()

    def _reaper_loop(self) -> None:
        while not self._stop_reaper.wait(timeout=5.0):
            try:
                reaped = self.web_registry.gc_once()
                for ws in reaped:
                    self.log(f"[web-reap] session={ws.session_id[:8]}…")
            except Exception as exc:
                self.log(f"[web-reaper-error] {exc!r}")


def serve_forever(
    bind_addr: str = "0.0.0.0",
    port: int = DEFAULT_PORT,
    idle_timeout: int = DEFAULT_IDLE_TIMEOUT_SECONDS,
    log_fn=None,
    name_registry: Optional[NameRegistry] = None,
    max_sessions: int = 8,
) -> None:
    """Block forever serving the BSG Adventure browser-play HTTP server.

    A `name_registry` should be passed when the TCP listener is also
    running, so name claims are shared across both transports."""
    import content  # noqa: F401  — register content eagerly

    if name_registry is None:
        name_registry = NameRegistry(max_sessions)
    server = BSGWebServer(
        (bind_addr, port),
        name_registry=name_registry,
        idle_timeout=idle_timeout,
        log_fn=log_fn,
    )
    server.log(
        f"BSG Adventure (HTTP) listening on http://{bind_addr}:{port} "
        f"(idle timeout {idle_timeout}s)"
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()
