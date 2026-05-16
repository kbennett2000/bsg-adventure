# Multiplayer Report

**Scope:** LAN multi-session hosting, per the design already documented in
[CLAUDE.md](CLAUDE.md). One host runs a server; multiple players on the home
network each connect from their own terminal and play their own independent
session. No shared world, no internet exposure.

---

## TL;DR

The architecture was designed for this from day one. The IO abstraction, the
`Session` class, per-player save paths, and the no-shared-mutable-state
discipline are already in place. **The missing pieces are a thin networking
layer (~200 lines) and a per-connection lifecycle that re-uses the existing
`Session.run()` loop verbatim.**

Recommended approach: **thread-per-connection with a `socketserver`-based
TCP server.** This is ~1 day of focused work for an MVP, including tests.

A full async refactor is *not* required and would be substantially more
invasive (every NPC dialogue and command handler is sync today; making them
async would touch ~3,500 lines for negligible per-session benefit on a home
LAN that will see ≤8 concurrent players).

---

## What's already in place

| Concern | Status |
|---|---|
| IO abstraction ([engine/io.py](engine/io.py)) | `IO` base class with `send()` / `receive()`; `LocalIO` and `ScriptedIO` implementations. **NetIO is the only missing implementation.** |
| Per-session loop ([engine/session.py](engine/session.py)) | `Session(io, world)` is fully self-contained. Sync. Returns `None` on quit or a dict on new-game-plus. Already replays cleanly for repeated session creation. |
| Per-player save paths ([engine/save.py](engine/save.py)) | `<BSG_SAVE_DIR>/<player_name>/` with sanitization (`[A-Za-z0-9_]{1,32}`). Atomic tmp+fsync+rename writes. Survives reboot. |
| Auto-resume on reconnect | `start_session_local` already loads `auto.json` if it exists for the player name. |
| Achievements file | Per-player JSON at `<saves>/<player>/achievements.json`. Same isolation. |
| Read-only content registries | `ROOMS`, `NPCS`, `ITEMS`, ambient `_REGISTERED` are populated once at content import and never mutated at runtime. Safe to share across concurrent sessions. |
| No global mutable game state | All mutable state lives in `WorldState`, which is per-session. Verified by `grep`. |
| Random module usage | All `random.choice` / `random.random` calls are CPython-thread-safe. Ordering becomes nondeterministic across concurrent sessions, which is fine for ambient flavor. |
| Title + name prompt | Currently in [main.py](main.py); already separated from `Session.run()`, so it can be moved into the per-connection handler without refactoring the loop. |

---

## What needs to change

### 1. NetIO — new IO implementation

Add a third class to [engine/io.py](engine/io.py) (or `engine/netio.py` if you
prefer to keep io.py small):

```python
class NetIO(IO):
    """Line-oriented TCP IO over a socket. Used by the server."""
    def __init__(self, rfile, wfile):
        self._rfile = rfile   # buffered binary read file
        self._wfile = wfile   # buffered binary write file

    def send(self, text: str) -> None:
        # Normalize \n to \r\n so telnet clients display correctly.
        self._wfile.write((text + "\r\n").encode("utf-8", errors="replace"))
        self._wfile.flush()

    def receive(self, prompt: str = "> ") -> str:
        if prompt:
            self._wfile.write(prompt.encode("utf-8"))
            self._wfile.flush()
        line = self._rfile.readline()
        if not line:
            return "quit"   # connection closed → graceful quit
        # Strip CR (telnet) and trailing whitespace; decode UTF-8 leniently.
        return line.decode("utf-8", errors="replace").rstrip("\r\n").rstrip()
```

This is the most important file. ~30 lines.

### 2. Server entry point — new `engine/server.py`

Use `socketserver.ThreadingTCPServer` so we don't have to refactor the sync
game loop into async. Each connection gets its own OS thread; the GIL is a
non-issue because the workload is purely IO-bound.

```python
import os
import socketserver
import threading

class BSGRequestHandler(socketserver.StreamRequestHandler):
    timeout = 1800  # 30 minute idle timeout

    def handle(self):
        from engine.io import NetIO
        from engine.session import Session
        from engine.world import new_world
        from main import show_title, prompt_for_name, build_world  # title + name prompt reused

        io = NetIO(self.rfile, self.wfile)
        try:
            show_title(io)
            name = prompt_for_name(io)
            if not self.server.claim_name(name):
                io.send("You're already aboard, specialist. Find another terminal.")
                return
            try:
                ng_plus_context = None
                while True:
                    if ng_plus_context:
                        io.send("── ALL OF THIS HAS HAPPENED BEFORE ──")
                    world = build_world(name, ng_plus_context)
                    session = Session(io=io, world=world)
                    next_action = session.run()
                    if not next_action or not next_action.get("ng_plus"):
                        break
                    ng_plus_context = next_action
            finally:
                self.server.release_name(name)
        except Exception:
            pass   # disconnect silently on socket errors


class BSGServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    MAX_SESSIONS = 8

    def __init__(self, server_address):
        super().__init__(server_address, BSGRequestHandler)
        self._active_names: set[str] = set()
        self._lock = threading.Lock()

    def claim_name(self, name: str) -> bool:
        with self._lock:
            if name in self._active_names or len(self._active_names) >= self.MAX_SESSIONS:
                return False
            self._active_names.add(name)
            return True

    def release_name(self, name: str) -> None:
        with self._lock:
            self._active_names.discard(name)


def serve_forever(bind_addr: str, port: int) -> None:
    import content  # noqa: F401  — triggers registration
    server = BSGServer((bind_addr, port))
    print(f"BSG Adventure listening on {bind_addr}:{port}")
    server.serve_forever()
```

~80 lines including blank lines and imports.

### 3. main.py — add a `--serve` flag

Currently main.py always runs local. Make it dispatch:

```python
def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--serve", action="store_true",
                   help="Run as LAN server (default for hosting).")
    p.add_argument("--local", action="store_true",
                   help="Single-player local terminal (current behavior).")
    p.add_argument("--port", type=int,
                   default=int(os.environ.get("BSG_PORT", "4404")))
    p.add_argument("--bind", default=os.environ.get("BSG_BIND_ADDR", "0.0.0.0"))
    args = p.parse_args()

    if args.serve:
        from engine.server import serve_forever
        serve_forever(args.bind, args.port)
        return 0

    # Existing local-play flow:
    io = LocalIO()
    show_title(io)
    name = prompt_for_name(io)
    ...
```

Backwards-compatible: `python3 main.py` with no flags stays local-only by
default, so existing local-play and tests don't change. The host runs
`python3 main.py --serve` (or you can flip the default; the CLAUDE.md plan
was `--serve` as default — pick whichever you prefer for ergonomics).

### 4. Same-name conflict policy

The `claim_name` / `release_name` pair on the server enforces *"one session
per player_name at a time."* CLAUDE.md already specified this:

> Same `player_name` connecting twice while a session is already live → the
> new connection gets "You're already aboard, specialist." and is refused.

This is critical because save files and the achievements file are not
designed for concurrent writers. Two sessions for the same player would race
on `auto.json` and `achievements.json`.

### 5. Idle timeout

`socketserver.StreamRequestHandler.timeout = 1800` causes `readline()` to
raise `socket.timeout` after 30 minutes of inactivity. The session's
autosave runs every 10 turns AND on graceful quit, so a timeout-disconnected
player loses at most 10 turns of progress.

To make this cleaner, the `NetIO.receive` could catch `socket.timeout` and
return a sentinel like `"quit"`, which the session loop already handles.

### 6. Max concurrent sessions

`MAX_SESSIONS = 8` on `BSGServer`. Refuses additional connections in
character: *"The frakkin' ship is full. Try again later."*

For a home LAN this cap is plenty. Configurable via env var.

### 7. Operational

- **systemd unit file** at `systemd/bsg-adventure.service` so the host
  auto-restarts after a reboot:

  ```ini
  [Unit]
  Description=BSG Adventure LAN Server
  After=network-online.target

  [Service]
  ExecStart=/usr/bin/python3 /opt/bsg-adventure/main.py --serve
  WorkingDirectory=/opt/bsg-adventure
  Environment=BSG_SAVE_DIR=/var/lib/bsg-adventure/saves
  Restart=on-failure
  User=bsg
  Group=bsg

  [Install]
  WantedBy=multi-user.target
  ```

- **Logging**: print connection/disconnection events with player name, source
  IP, duration, and ending (if any) to stdout. systemd captures stdout to
  journald automatically.

- **`BSG_SAVE_DIR`** should point to a path *outside* the install directory
  (e.g., `/var/lib/bsg-adventure/saves`) so package upgrades don't blow away
  save files. The env-var override already supports this.

- **README updates**: add a "Hosting" section with the systemd template and
  the `nc <host> 4404` client instruction.

---

## Concrete file changelist

| File | Change | Approx. LoC |
|---|---|---|
| `engine/io.py` | Add `NetIO` class | +30 |
| `engine/server.py` | **NEW**: ThreadingTCPServer + handler + name registry | +80 |
| `main.py` | Add `--serve` / `--port` / `--bind` flags | +25 |
| `systemd/bsg-adventure.service` | **NEW**: example unit file | +15 |
| `README.md` | Add Hosting section | +30 |
| `tests/test_server.py` | **NEW**: two-concurrent-sessions test, same-name refusal, idle timeout | +120 |

**Total: ~300 lines, one new module, zero changes to game logic.**

---

## Testing plan

The existing 159 tests all pass through `Session(ScriptedIO(...), world)` —
none of them go through the network. They stay green automatically.

New tests in `tests/test_server.py`:

1. **Smoke test: server starts and accepts a connection.** Bind to
   `127.0.0.1:0` (kernel-assigned port), spawn a client socket in the same
   process, send a name + `quit`, confirm clean disconnect.

2. **Two concurrent sessions don't interfere.** Spawn two clients with
   different names. Each takes a different action (one drinks the canteen,
   one talks to Tigh). After both quit, load their save files and confirm
   distinct state.

3. **Same-name refusal.** Spawn a client with name "Kara", let it sit at the
   first prompt. Spawn a second client with the same name. The second gets
   refused and disconnects.

4. **Max-sessions refusal.** Set `MAX_SESSIONS = 2` for the test, spawn 3
   clients, confirm the third is refused.

5. **Idle timeout.** Set `timeout = 1` for the test, connect, don't send
   input, confirm the server disconnects after ~1 second and triggers an
   autosave.

6. **NetIO encoding.** Send a line with Unicode (the player's name contains
   only `[A-Za-z0-9_]` but the game OUTPUT contains box-drawing characters
   `──`). Confirm the client receives correct UTF-8.

All six tests fit in a single file, all use the existing `Session` /
`world` infrastructure unchanged, all use the standard library `socket`
module.

---

## Risks and gotchas

### Telnet vs raw TCP

The server speaks raw line-oriented text. Modern clients:

- **`nc` / `ncat`**: works out of the box. No protocol handshake.
- **`telnet`**: works, but sends CRLF and may try to negotiate IAC options
  (option bytes 0xFF). NetIO already handles CRLF; IAC bytes get rendered
  as garbage UTF-8 but don't crash. Optionally, NetIO can strip leading
  IAC byte-sequences from received input. Add only if a player complains.
- **Custom Python client**: trivial — `socket.create_connection()` + line
  IO. Could ship one in `tools/client.py` for convenience, but a player
  with `nc` doesn't need it.

### Save-file concurrency

Two threads writing to `<player>/auto.json` would race. The `claim_name`
mechanism prevents this by refusing the second concurrent session for the
same name. **Do not weaken this without adding per-file locking.**

### Random module

`random.choice` and `random.random` share a process-wide RNG. Concurrent
sessions see interleaved draws, so ambient events and corridor encounters
become globally nondeterministic. For ambient flavor this is desirable.
**If you ever want per-session determinism (for replays or seeded runs),
each Session needs its own `random.Random()` instance** stored on
`WorldState` — moderate refactor.

### Thread safety of imports

`import content` registers everything at first import. If two connections
arrive *simultaneously* during cold start, both might try to import
content. Python's import lock makes this safe, but to be extra-safe,
`serve_forever()` should `import content` before calling
`server.serve_forever()`. Already shown above.

### NPC dialogue with side effects

Many dialogue handlers mutate `world.npc_state` and `world.flags`. Those
mutations are scoped to the per-session `WorldState`, so there is no
cross-session contamination — but a code reviewer should confirm there
are no module-level state mutations introduced after this point.

A quick audit script:

```bash
grep -nE "^[A-Z_]+ ?\[" content/ engine/   # module-level mutable lookups
```

### Output buffering

Python's `print()` is line-buffered when stdout is a TTY and block-buffered
when piped. With NetIO we explicitly `flush()` after every `send()`, so
players don't see paragraphs arrive 30 seconds late. Important — covered
by NetIO's implementation above.

### LAN-only binding

Default bind is `0.0.0.0:4404` which exposes the server on every interface.
**Documentation must be explicit** that the host should not forward this
port through their router. There is no auth, no rate limiting, no input
sanitization beyond name validation. Trivial to abuse from the internet.
Mitigations if needed later: bind to a specific LAN IP, or add a
`BSG_ALLOWED_CIDR` env-var allowlist.

### Achievements file persistence

The achievements file uses non-atomic writes today
([content/achievements.py](content/achievements.py): `p.write_text(...)`).
A crash mid-write would corrupt it. Under single-player local play this is
fine; under multiplayer it's still fine because we enforce one session per
player. But if you ever loosen the same-name policy, also harden this
write to use the same tmp+rename pattern as `engine/save.py`.

---

## Out of scope (deliberately)

These are *not* required for the LAN multiplayer shipping target and
should be explicitly punted:

- **TLS / authentication.** LAN only, trusted network.
- **Encryption of save files.** No.
- **Web client / WebSocket protocol.** Raw TCP is sufficient.
- **Database backend.** Per-player JSON files are correct for this scale.
- **Player-to-player communication (chat).** Each session is independent;
  there is no in-game mechanism for one player to see another. Adding chat
  would be its own design and a different shape of game.
- **Live observability of other players' sessions.** Same as above.
- **Cross-session achievements or leaderboards.** Possible later via a
  global-rather-than-per-player achievements directory, but the current
  design ships each player their own private history.

---

## MVP scope and effort estimate

### MVP (ship-worthy)

- `engine/io.py`: NetIO
- `engine/server.py`: ThreadingTCPServer
- `main.py`: `--serve` flag
- `tests/test_server.py`: 3 of the 6 tests (smoke, two concurrent, same-name)
- README update

**Effort: 4–6 hours of focused work.** This is genuinely small — the heavy
lifting has been done in the IO abstraction and session isolation.

### Polish (post-MVP)

- All 6 server tests
- Idle timeout cleanly logged in character
- Max-sessions refusal in character
- systemd unit file
- Optional `tools/client.py` Python client

**Additional effort: 2–4 hours.**

### Full operational

- Logging to journald
- BSG_ALLOWED_CIDR allowlist
- Health-check endpoint (so a monitor can confirm the server is alive)
- Graceful shutdown that warns connected players

**Additional effort: 3–5 hours.** Only needed if you actually plan to keep
the server running 24/7.

---

## Suggested implementation order

1. **NetIO + a smoke test that round-trips one line.** This proves the IO
   abstraction holds. (~1 hour.)
2. **`engine/server.py` minimal accept-and-spawn-session.** Test by
   `nc localhost 4404` from a second terminal. (~1 hour.)
3. **`main.py --serve` flag + name claim/release.** (~30 minutes.)
4. **Two-concurrent-sessions test.** This is the load-bearing correctness
   test — if it passes, you're done. (~1 hour.)
5. **README hosting section + systemd template.** (~30 minutes.)
6. **Idle timeout + max sessions polish.** (~1 hour.)

After step 4, players on the LAN can connect and play. Steps 5–6 make it
production-pleasant.

---

## What this report does NOT change

To be explicit: **no game content, NPC dialogue, room descriptions,
endings, achievements, or game loop logic needs to change for multiplayer.**
The 159 existing tests are unaffected. The local-play experience is
unchanged. This is a pure additive feature.
