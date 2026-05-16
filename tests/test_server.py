"""End-to-end LAN server tests. Uses real sockets bound to 127.0.0.1 on a
kernel-assigned port; spawns the server in a background thread and connects
from the same process using stdlib `socket`.

All tests are stdlib-only and run under `python3 run_tests.py`."""

import contextlib
import os
import socket
import tempfile
import threading
import time
from pathlib import Path

import content  # noqa: F401  — ensure registration happens before threads spawn

from engine.server import BSGServer, DEFAULT_IDLE_TIMEOUT_SECONDS


# ─── shared infrastructure ─────────────────────────────────────────────────────


@contextlib.contextmanager
def running_server(max_sessions=8, idle_timeout=DEFAULT_IDLE_TIMEOUT_SECONDS, save_dir=None):
    """Start a BSGServer on 127.0.0.1:0 (kernel-assigned port), yield (server, port).
    Tears down on exit."""
    if save_dir is not None:
        os.environ["BSG_SAVE_DIR"] = str(save_dir)

    server = BSGServer(
        ("127.0.0.1", 0),
        max_sessions=max_sessions,
        idle_timeout=idle_timeout,
        log_fn=lambda msg: None,  # silence server logs during tests
    )
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _connect(port: int, timeout: float = 5.0):
    """Returns (socket, rfile, wfile) for a client. Use rfile.readline() to
    receive a single line, wfile.write(b'...\\n') + flush() to send."""
    s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    s.settimeout(timeout)
    rfile = s.makefile("rb", buffering=0)
    wfile = s.makefile("wb", buffering=0)
    return s, rfile, wfile


def _send_line(wfile, text: str) -> None:
    wfile.write((text + "\n").encode("utf-8"))
    wfile.flush()


def _read_until(rfile, marker: str, max_lines: int = 500) -> str:
    """Read lines until we see `marker` substring, or exhaust max_lines / EOF.
    Returns everything read so far."""
    buf = []
    for _ in range(max_lines):
        line = rfile.readline()
        if not line:
            break
        decoded = line.decode("utf-8", errors="replace")
        buf.append(decoded)
        if marker in decoded:
            break
    return "".join(buf)


def _drain_for(rfile, seconds: float = 0.4) -> str:
    """Best-effort read for a short window. Used to flush server output and
    advance to the next prompt."""
    rfile_sock = rfile.raw if hasattr(rfile, "raw") else None
    deadline = time.time() + seconds
    buf = []
    while time.time() < deadline:
        try:
            rfile._sock.settimeout(0.05) if hasattr(rfile, "_sock") else None  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            line = rfile.readline()
        except socket.timeout:
            continue
        except Exception:
            break
        if not line:
            break
        buf.append(line.decode("utf-8", errors="replace"))
    return "".join(buf)


# ─── tests ─────────────────────────────────────────────────────────────────────


def test_server_starts_and_accepts_a_connection():
    """A client can connect, complete name entry, and quit cleanly."""
    with tempfile.TemporaryDirectory() as tmp, running_server(save_dir=tmp) as (_, port):
        s, rfile, wfile = _connect(port)
        try:
            # Title art + press-enter prompt
            _ = _read_until(rfile, "press enter", max_lines=200)
            _send_line(wfile, "")  # press enter
            # Name prompt
            _ = _read_until(rfile, "STATE YOUR NAME", max_lines=200)
            _send_line(wfile, "TestPlayer")
            # Acknowledgment
            _ = _read_until(rfile, "ACKNOWLEDGED", max_lines=200)
            # Opening room render
            _ = _read_until(rfile, "ENVIRONMENTAL CONTROL", max_lines=200)
            # Quit
            _send_line(wfile, "quit")
            tail = _read_until(rfile, "Frak out", max_lines=200)
            assert "Frak out" in tail
        finally:
            s.close()


def _drive_client_batch(port: int, name: str, actions: list[str]) -> None:
    """Open a connection, blast all input lines at once, read until the server
    closes the socket (guaranteeing the handler's finally has fired and the
    autosave is on disk), then return."""
    s, rfile, wfile = _connect(port, timeout=15)
    try:
        # All input lines up front; the server reads them in order. Empty first
        # line is the press-enter; second is the name; then actions, then quit.
        payload = "\n".join([""] + [name] + actions + ["quit", ""])
        wfile.write(payload.encode("utf-8"))
        wfile.flush()
        # Read until EOF. The handler's finally block (which releases the name
        # AND runs after the autosave) closes the socket; reading to EOF means
        # the save file is definitely on disk before we return.
        while True:
            chunk = rfile.read(4096)
            if not chunk:
                break
    finally:
        s.close()


def test_two_concurrent_sessions_do_not_interfere():
    """Two clients with different names play independently. Their save files
    end up reflecting their distinct actions."""
    with tempfile.TemporaryDirectory() as tmp, running_server(save_dir=tmp) as (_, port):
        t_a = threading.Thread(
            target=_drive_client_batch,
            args=(port, "Apollo_Test", ["go east"]),
        )
        t_b = threading.Thread(
            target=_drive_client_batch,
            args=(port, "Boomer_Test", ["take mop"]),
        )
        t_a.start()
        t_b.start()
        t_a.join(timeout=15)
        t_b.join(timeout=15)
        assert not t_a.is_alive() and not t_b.is_alive(), "client threads stuck"

        from engine import save as save_module
        apollo_save = save_module.load_world("Apollo_Test", "auto")
        boomer_save = save_module.load_world("Boomer_Test", "auto")

        # Apollo went east → should be in corridor_c12.
        assert apollo_save.current_room == "corridor_c12", (
            f"Apollo's session: expected corridor_c12, got {apollo_save.current_room}"
        )
        # Boomer took the mop → should have it in inventory.
        assert "mop" in boomer_save.inventory, (
            f"Boomer's session: mop missing from inventory {boomer_save.inventory}"
        )
        # And they didn't cross-contaminate.
        assert "mop" not in apollo_save.inventory
        assert boomer_save.current_room == "env_control"


def test_same_name_second_connection_is_refused():
    """If a player is already aboard with name X, a second connection with the
    same name gets a refusal and disconnects."""
    with tempfile.TemporaryDirectory() as tmp, running_server(save_dir=tmp) as (server, port):
        s1, rfile1, wfile1 = _connect(port)
        try:
            _read_until(rfile1, "press enter", max_lines=200)
            _send_line(wfile1, "")
            _read_until(rfile1, "STATE YOUR NAME", max_lines=200)
            _send_line(wfile1, "Duplicate")
            _read_until(rfile1, "ACKNOWLEDGED", max_lines=200)
            # Player 1 is now claimed. Give the server a beat to register.
            time.sleep(0.1)
            assert server.active_count == 1

            # Second connection with same name → refusal.
            s2, rfile2, wfile2 = _connect(port)
            try:
                _read_until(rfile2, "press enter", max_lines=200)
                _send_line(wfile2, "")
                _read_until(rfile2, "STATE YOUR NAME", max_lines=200)
                _send_line(wfile2, "Duplicate")
                refusal_tail = _read_until(rfile2, "already a Specialist", max_lines=200)
                assert "already a Specialist Duplicate" in refusal_tail
            finally:
                s2.close()

            # First connection still alive.
            assert server.active_count == 1
        finally:
            _send_line(wfile1, "quit")
            try:
                _read_until(rfile1, "Frak out", max_lines=200)
            except Exception:
                pass
            s1.close()


def test_max_sessions_cap_refuses_overflow():
    """When max_sessions is exceeded, the next connection gets the 'ship is
    full' refusal."""
    with tempfile.TemporaryDirectory() as tmp, running_server(
        max_sessions=2, save_dir=tmp
    ) as (server, port):
        clients = []
        try:
            for i, name in enumerate(["Cap_A", "Cap_B"]):
                s, rfile, wfile = _connect(port)
                clients.append((s, rfile, wfile))
                _read_until(rfile, "press enter", max_lines=200)
                _send_line(wfile, "")
                _read_until(rfile, "STATE YOUR NAME", max_lines=200)
                _send_line(wfile, name)
                _read_until(rfile, "ACKNOWLEDGED", max_lines=200)
                time.sleep(0.1)
            assert server.active_count == 2

            # Third connection — different name — should still refuse (cap).
            s3, rfile3, wfile3 = _connect(port)
            try:
                _read_until(rfile3, "press enter", max_lines=200)
                _send_line(wfile3, "")
                _read_until(rfile3, "STATE YOUR NAME", max_lines=200)
                _send_line(wfile3, "Overflow")
                tail = _read_until(rfile3, "ship is full", max_lines=200)
                assert "ship is full" in tail
            finally:
                s3.close()
        finally:
            for s, rfile, wfile in clients:
                try:
                    _send_line(wfile, "quit")
                    _read_until(rfile, "Frak out", max_lines=200)
                except Exception:
                    pass
                s.close()


def test_idle_timeout_disconnects_silent_client():
    """A client that stops sending input gets disconnected after the idle
    timeout. The session autosaves on the way out."""
    with tempfile.TemporaryDirectory() as tmp, running_server(
        idle_timeout=1, save_dir=tmp
    ) as (server, port):
        s, rfile, wfile = _connect(port, timeout=10)
        try:
            _read_until(rfile, "press enter", max_lines=200)
            _send_line(wfile, "")
            _read_until(rfile, "STATE YOUR NAME", max_lines=200)
            _send_line(wfile, "Idler")
            _read_until(rfile, "ENVIRONMENTAL CONTROL", max_lines=200)
            # Now stop sending input. Within ~1s the server should disconnect.
            time.sleep(2.0)

            # Server should have released the name.
            assert server.active_count == 0, (
                f"expected idle timeout to clean up; active_count={server.active_count}"
            )

            # Autosave should exist (session disconnected via 'quit' sentinel).
            from engine import save as save_module
            assert save_module.has_save("Idler", "auto"), (
                "expected autosave to be written before timeout disconnect"
            )
        finally:
            s.close()


def test_netio_handles_crlf_line_endings():
    """Clients that send CRLF (telnet-style) are accepted just like LF (nc)."""
    with tempfile.TemporaryDirectory() as tmp, running_server(save_dir=tmp) as (_, port):
        s, rfile, wfile = _connect(port)
        try:
            _read_until(rfile, "press enter", max_lines=200)
            # Send press-enter as bare CRLF (telnet client style).
            wfile.write(b"\r\n")
            wfile.flush()
            _read_until(rfile, "STATE YOUR NAME", max_lines=200)
            # Name with CRLF.
            wfile.write(b"CRLF_Tester\r\n")
            wfile.flush()
            ack = _read_until(rfile, "ACKNOWLEDGED", max_lines=200)
            assert "CRLF_TESTER" in ack  # uppercased in the ack line
            # Quit with CRLF.
            wfile.write(b"quit\r\n")
            wfile.flush()
            _read_until(rfile, "Frak out", max_lines=200)
        finally:
            s.close()


def test_server_logs_can_be_redirected():
    """The log function injection works (so prod can write to journald)."""
    logged = []
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        server = BSGServer(
            ("127.0.0.1", 0),
            max_sessions=4,
            idle_timeout=DEFAULT_IDLE_TIMEOUT_SECONDS,
            log_fn=lambda msg: logged.append(msg),
        )
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            s, rfile, wfile = _connect(port)
            try:
                _read_until(rfile, "press enter", max_lines=200)
                _send_line(wfile, "")
                _read_until(rfile, "STATE YOUR NAME", max_lines=200)
                _send_line(wfile, "Logged")
                _read_until(rfile, "ACKNOWLEDGED", max_lines=200)
                _send_line(wfile, "quit")
                _read_until(rfile, "Frak out", max_lines=200)
                # Give the server's finally-block a beat to fire its disconnect log.
                time.sleep(0.2)
            finally:
                s.close()
            # We should see at least connect and session-start events for "Logged".
            joined = "\n".join(logged)
            assert "[connect]" in joined
            assert "Logged" in joined
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
