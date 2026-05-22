"""Tests for the browser/HTTP transport.

Spins up a real BSGWebServer on an ephemeral loopback port and drives it with
stdlib `urllib.request`. The Session machinery is unchanged from TCP — these
tests cover the new pieces: the SSE+POST protocol, session lifecycle, the
shared NameRegistry across transports, idle/grace GC, and the LAN-only
no-external-URL invariant for the static assets."""

import json
import os
import re
import tempfile
import threading
import time
import urllib.error
import urllib.request

import content  # noqa: F401 — register content for spawned game threads

from engine.name_registry import NameRegistry
from engine.webserver import BSGWebServer, WebSessionRegistry


# ─── harness ────────────────────────────────────────────────────────────────


class _ServerCtx:
    """Spin up a BSGWebServer on a free port for the duration of a `with` block."""

    def __init__(self, max_sessions: int = 4, idle_timeout: int = 60,
                 grace_after_disconnect: int = 5, name_registry=None) -> None:
        self.max_sessions = max_sessions
        self.idle_timeout = idle_timeout
        self.grace_after_disconnect = grace_after_disconnect
        self.name_registry = name_registry

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["BSG_SAVE_DIR"] = self._tmp.name
        reg = self.name_registry or NameRegistry(self.max_sessions)
        self.server = BSGWebServer(
            ("127.0.0.1", 0),
            name_registry=reg,
            idle_timeout=self.idle_timeout,
            grace_after_disconnect=self.grace_after_disconnect,
            log_fn=lambda _msg: None,
        )
        self.port = self.server.server_address[1]
        self._thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self._thread.start()
        self.url = f"http://127.0.0.1:{self.port}"
        return self

    def __exit__(self, *exc) -> None:
        try:
            self.server.shutdown()
        except Exception:
            pass
        try:
            self.server.server_close()
        except Exception:
            pass
        self._tmp.cleanup()

    # ── per-test helpers ───────────────────────────────────────────────────

    def spawn(self) -> str:
        req = urllib.request.Request(self.url + "/spawn", method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.load(r)["session_id"]

    def post_input(self, sid: str, line: str) -> int:
        req = urllib.request.Request(
            self.url + f"/input?session={sid}",
            data=line.encode("utf-8"),
            method="POST",
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status

    def post_close(self, sid: str) -> int:
        req = urllib.request.Request(
            self.url + f"/close?session={sid}", method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status

    def open_sse(self, sid: str) -> "_SSEReader":
        return _SSEReader(self.url + f"/events?session={sid}")


class _SSEReader:
    """Background reader that collects SSE `data:` payloads as decoded text."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.texts: list[str] = []
        self.events: list[str] = []
        self.done = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            with urllib.request.urlopen(self.url, timeout=10) as r:
                for raw in r:
                    if self._stop.is_set():
                        break
                    line = raw.decode("utf-8", errors="replace").rstrip("\n").rstrip("\r")
                    if line.startswith("data: "):
                        payload = line[6:]
                        try:
                            obj = json.loads(payload)
                            if "text" in obj:
                                self.texts.append(obj["text"])
                        except json.JSONDecodeError:
                            self.texts.append(payload)
                    elif line.startswith("event: "):
                        ev = line[7:]
                        self.events.append(ev)
                        if ev == "end":
                            self.done.set()
                            break
        except Exception:
            pass
        finally:
            self.done.set()

    def wait_for(self, predicate, timeout: float = 5.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate("\n".join(self.texts)):
                return True
            time.sleep(0.05)
        return False

    def joined(self) -> str:
        return "\n".join(self.texts)

    def close(self) -> None:
        self._stop.set()


# ─── helpers to drive a session through the first prompts ───────────────────


def _press_enter_and_name(ctx: _ServerCtx, sid: str, name: str,
                          reader: _SSEReader) -> None:
    """Push past the title screen (press enter) and name prompt."""
    assert reader.wait_for(lambda s: "press enter to begin" in s.lower()), \
        "title screen never rendered"
    ctx.post_input(sid, "")  # press enter
    assert reader.wait_for(lambda s: "STATE YOUR NAME" in s), \
        "name prompt never rendered"
    ctx.post_input(sid, name)
    assert reader.wait_for(
        lambda s: "ENVIRONMENTAL CONTROL" in s.upper()
    ), "room description never rendered"


# ─── static assets ──────────────────────────────────────────────────────────


def test_index_html_serves_and_is_self_contained():
    """Index HTML must not pull external resources — game is LAN-only and
    must work with no internet."""
    with _ServerCtx() as ctx:
        with urllib.request.urlopen(ctx.url + "/") as r:
            html = r.read().decode("utf-8")
    assert "<title>BSG Adventure</title>" in html
    # No external script/stylesheet/font/img sources.
    assert "http://" not in html.lower(), (
        "index.html references external http:// URL"
    )
    # 'https://' would also be a leak; check carefully (allow 'https' as
    # plain text inside content, but not as a URL).
    assert not re.search(r'src\s*=\s*"\s*https://', html, re.IGNORECASE)
    assert not re.search(r'href\s*=\s*"\s*https://', html, re.IGNORECASE)
    assert not re.search(r"@import\s+url\s*\(", html, re.IGNORECASE)


def test_css_has_no_external_urls():
    with _ServerCtx() as ctx:
        with urllib.request.urlopen(ctx.url + "/style.css") as r:
            css = r.read().decode("utf-8")
    assert "http://" not in css
    assert "https://" not in css
    assert "@import" not in css


def test_app_js_has_no_external_urls():
    with _ServerCtx() as ctx:
        with urllib.request.urlopen(ctx.url + "/app.js") as r:
            js = r.read().decode("utf-8")
    # Allow plain English uses of the word "http" (e.g. comments) by
    # checking for the URL form specifically.
    assert "http://" not in js, "app.js contains an http:// URL"
    assert "https://" not in js, "app.js contains an https:// URL"
    # No third-party loader patterns either.
    assert "fetch(\"http" not in js
    assert "import(" not in js
    assert "importScripts" not in js


def test_healthz():
    with _ServerCtx() as ctx:
        with urllib.request.urlopen(ctx.url + "/healthz") as r:
            assert r.status == 200
            assert json.load(r) == {"ok": True}


# ─── session lifecycle ──────────────────────────────────────────────────────


def test_spawn_returns_a_session_id():
    with _ServerCtx() as ctx:
        sid = ctx.spawn()
        # 32 hex chars (16 random bytes via secrets.token_hex)
        assert re.fullmatch(r"[0-9a-f]{32}", sid)


def test_full_round_trip_title_to_room_description():
    with _ServerCtx() as ctx:
        sid = ctx.spawn()
        reader = ctx.open_sse(sid)
        _press_enter_and_name(ctx, sid, "WebTester", reader)
        # After name, the INTERCOM line should also appear.
        assert reader.wait_for(lambda s: "INTERCOM: ACKNOWLEDGED" in s)
        # Tear down cleanly.
        ctx.post_input(sid, "quit")
        assert reader.done.wait(timeout=5), "SSE end event never delivered"


def test_input_route_404s_for_unknown_session():
    with _ServerCtx() as ctx:
        try:
            ctx.post_input("deadbeef" * 4, "anything")
        except urllib.error.HTTPError as e:
            assert e.code == 404
        else:
            raise AssertionError("expected 404 for unknown session")


def test_input_too_large_is_rejected():
    with _ServerCtx() as ctx:
        sid = ctx.spawn()
        oversized = "x" * 9000
        try:
            ctx.post_input(sid, oversized)
        except urllib.error.HTTPError as e:
            assert e.code == 413, e.code
        else:
            raise AssertionError("expected 413 for >8KB input")


def test_events_route_404s_for_unknown_session():
    with _ServerCtx() as ctx:
        try:
            with urllib.request.urlopen(ctx.url + "/events?session=nope") as r:
                pass
        except urllib.error.HTTPError as e:
            assert e.code == 404
        else:
            raise AssertionError("expected 404 for unknown session on /events")


# ─── concurrent sessions don't interfere ────────────────────────────────────


def test_two_concurrent_browser_sessions_do_not_bleed():
    """Two browser tabs (different names) should each get their own world."""
    with _ServerCtx() as ctx:
        sid1 = ctx.spawn()
        sid2 = ctx.spawn()
        r1 = ctx.open_sse(sid1)
        r2 = ctx.open_sse(sid2)

        _press_enter_and_name(ctx, sid1, "Alpha", r1)
        _press_enter_and_name(ctx, sid2, "Bravo", r2)

        # Player 1 issues a flavor verb that's distinctive.
        ctx.post_input(sid1, "frak")
        time.sleep(0.3)
        # Player 2 issues a different distinctive verb.
        ctx.post_input(sid2, "salute")
        time.sleep(0.3)

        # Each player's transcript should reflect ONLY their own commands.
        # We check the FRAK output keywords go to r1, SALUTE keywords to r2.
        joined1 = r1.joined()
        joined2 = r2.joined()
        assert "ALPHA" in joined1.upper()
        assert "BRAVO" in joined2.upper()
        assert "ALPHA" not in joined2.upper()
        assert "BRAVO" not in joined1.upper()

        ctx.post_input(sid1, "quit")
        ctx.post_input(sid2, "quit")
        assert r1.done.wait(timeout=5)
        assert r2.done.wait(timeout=5)


# ─── name claim shared with TCP ─────────────────────────────────────────────


def test_name_already_claimed_is_refused_with_intercom_message():
    """If another transport (or another web tab) has already claimed the
    name, the second connection gets the in-character refusal and the
    session ends."""
    registry = NameRegistry(max_sessions=4)
    # Pre-claim the name as if a TCP connection already holds it.
    assert registry.claim("Tigh")
    try:
        with _ServerCtx(name_registry=registry) as ctx:
            sid = ctx.spawn()
            reader = ctx.open_sse(sid)
            assert reader.wait_for(lambda s: "press enter to begin" in s.lower())
            ctx.post_input(sid, "")
            assert reader.wait_for(lambda s: "STATE YOUR NAME" in s)
            ctx.post_input(sid, "Tigh")
            # Refusal message contains 'already a Specialist Tigh aboard'.
            assert reader.wait_for(lambda s: "already a Specialist" in s)
            # SSE should end shortly after the refusal.
            assert reader.done.wait(timeout=5)
    finally:
        registry.release("Tigh")


def test_max_sessions_cap_is_enforced_across_browser_tabs():
    """A registry capped at 2 cannot host a 3rd named session."""
    registry = NameRegistry(max_sessions=2)
    with _ServerCtx(name_registry=registry) as ctx:
        sids = [ctx.spawn() for _ in range(3)]
        readers = [ctx.open_sse(s) for s in sids]

        # First two should be admitted.
        for r, sid, n in zip(readers[:2], sids[:2], ["One", "Two"]):
            assert r.wait_for(lambda s: "press enter to begin" in s.lower())
            ctx.post_input(sid, "")
            assert r.wait_for(lambda s: "STATE YOUR NAME" in s)
            ctx.post_input(sid, n)
            assert r.wait_for(lambda s: "ENVIRONMENTAL CONTROL" in s.upper())

        # Third one should be refused at name claim.
        assert readers[2].wait_for(lambda s: "press enter to begin" in s.lower())
        ctx.post_input(sids[2], "")
        assert readers[2].wait_for(lambda s: "STATE YOUR NAME" in s)
        ctx.post_input(sids[2], "Three")
        assert readers[2].wait_for(
            lambda s: "frakkin' ship is full" in s.lower()
        )


# ─── reaper / GC ────────────────────────────────────────────────────────────


def test_web_session_registry_reaps_dead_threads():
    reg = WebSessionRegistry(idle_timeout=3600, grace_after_disconnect=3600)
    ws = reg.create()
    # No thread → registry considers it dead and reaps.
    reaped = reg.gc_once()
    assert ws in reaped
    assert reg.get(ws.session_id) is None


def test_web_session_registry_reaps_idle_sessions():
    """A session with no activity past the idle timeout is reaped."""
    reg = WebSessionRegistry(idle_timeout=0, grace_after_disconnect=3600)
    ws = reg.create()
    ws.thread = threading.Thread(target=lambda: time.sleep(60), daemon=True)
    ws.thread.start()
    ws.last_activity = time.time() - 100
    reaped = reg.gc_once()
    assert ws in reaped


def test_close_endpoint_signals_session_to_exit():
    """POSTing /close on a session causes the SSE stream to emit the end
    event and the session thread to exit cleanly."""
    with _ServerCtx() as ctx:
        sid = ctx.spawn()
        reader = ctx.open_sse(sid)
        assert reader.wait_for(lambda s: "press enter to begin" in s.lower())
        ctx.post_close(sid)
        # Session should wind down on its own.
        assert reader.done.wait(timeout=5)
