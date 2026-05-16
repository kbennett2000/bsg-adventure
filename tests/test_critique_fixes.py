"""Regression tests for the eight critique fixes.

Each test pins the behavior introduced by a specific fix so it can't silently
regress. Tests are stdlib-only (no pytest); run via `python3 run_tests.py`."""

import json
import os
import socket
import tempfile
import threading
import time
from pathlib import Path

import content  # noqa: F401


# ─── Fix #1: no duplicate _npc_visible ───────────────────────────────────────


def test_no_duplicate_npc_visible_definition():
    """The function should be defined exactly once in engine/commands.py."""
    import inspect
    from engine import commands
    src = inspect.getsource(commands)
    occurrences = src.count("def _npc_visible(")
    assert occurrences == 1, (
        f"_npc_visible should be defined once, found {occurrences} definitions"
    )


# ─── Fix #2: no `if self._check_collapse(): pass` no-op ──────────────────────


def test_no_op_collapse_wrapper_removed():
    """The session loop should call _check_collapse() directly, not wrap it
    in an if/pass."""
    import inspect
    from engine import session
    src = inspect.getsource(session.Session.run)
    assert "if self._check_collapse():" not in src
    assert "self._check_collapse()" in src


# ─── Fix #3: `use X on Y` actually dispatches ─────────────────────────────────


def test_use_x_on_y_routes_through_on_use_with():
    """When an item defines on_use_with[target_id], `use X on Y` should call
    that handler instead of returning the canned 'nothing happens' line."""
    from engine.io import ScriptedIO
    from engine.session import Session
    from engine.world import new_world
    from engine.registry import ITEMS

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp

        # Attach an ad-hoc on_use_with handler to the mop targeting the locker.
        # We do this on the live registered item — the test cleans up after.
        marker = []
        def handler(world):
            marker.append("dispatched")
            return "You use the mop on the locker. The locker is briefly tidier."

        original = ITEMS["mop"].on_use_with
        ITEMS["mop"].on_use_with = {"locker": handler}
        try:
            world = new_world("UseTest", "env_control")
            world.visited_rooms.append("env_control")
            world.inventory.append("mop")
            io = ScriptedIO(["use mop on locker", "quit"])
            Session(io=io, world=world).run()
            assert marker == ["dispatched"], (
                "use X on Y should have routed through on_use_with; "
                f"transcript tail: {io.outputs[-3:]}"
            )
            assert "briefly tidier" in io.transcript
        finally:
            ITEMS["mop"].on_use_with = original


def test_use_x_on_y_falls_back_when_no_handler_registered():
    """If no handler exists for this (item, target) pair, we still get the
    canned 'nothing happens' line — the player learns nothing happens, not
    that the verb is broken."""
    from engine.io import ScriptedIO
    from engine.session import Session
    from engine.world import new_world

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("UseTest", "env_control")
        world.visited_rooms.append("env_control")
        world.inventory.append("mop")
        io = ScriptedIO(["use mop on locker", "quit"])
        Session(io=io, world=world).run()
        assert "Nothing happens" in io.transcript


def test_use_x_on_unresolvable_target_explains():
    """If the target can't be resolved, tell the player so."""
    from engine.io import ScriptedIO
    from engine.session import Session
    from engine.world import new_world

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("UseTest", "env_control")
        world.visited_rooms.append("env_control")
        world.inventory.append("mop")
        io = ScriptedIO(["use mop on basestar", "quit"])
        Session(io=io, world=world).run()
        assert "basestar" in io.transcript and "don't see" in io.transcript


# ─── Fix #5: dropped client at name prompt doesn't become player 'quit' ──────


def test_prompt_for_name_rejects_quit_verb_as_name():
    """Typing 'quit' at the name prompt should NOT create a player named
    'quit'; it should raise Disconnected so the caller can exit cleanly."""
    from engine.io import Disconnected, ScriptedIO
    from main import prompt_for_name

    for reserved in ("quit", "exit", "q", "QUIT", "Exit", "Q"):
        io = ScriptedIO([reserved])
        try:
            prompt_for_name(io)
        except Disconnected:
            continue  # this is the expected outcome
        raise AssertionError(f"prompt_for_name accepted {reserved!r} as a player name")


def test_dropped_connection_does_not_create_quit_save():
    """End-to-end via the LAN server: a client that connects and immediately
    drops at the name prompt should NOT result in `saves/quit/` being created."""
    from engine.server import BSGServer, DEFAULT_IDLE_TIMEOUT_SECONDS

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        server = BSGServer(
            ("127.0.0.1", 0),
            max_sessions=4,
            idle_timeout=DEFAULT_IDLE_TIMEOUT_SECONDS,
            log_fn=lambda _: None,
        )
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            # Connect, read until the name prompt appears, then drop.
            s = socket.create_connection(("127.0.0.1", port), timeout=5)
            s.settimeout(5)
            rf = s.makefile("rb", buffering=0)
            wf = s.makefile("wb", buffering=0)
            # Skip past press-enter and into the name prompt.
            wf.write(b"\n")
            wf.flush()
            # Wait for the name prompt to appear, then disconnect.
            for _ in range(300):
                line = rf.readline()
                if not line:
                    break
                if b"STATE YOUR NAME" in line:
                    break
            s.close()
            # Give the server a moment to clean up.
            time.sleep(0.5)
            # No saves/quit/ should have been created.
            assert not (Path(tmp) / "quit").exists(), (
                f"server created a save for player 'quit' from a dropped client. "
                f"Contents: {list(Path(tmp).iterdir())}"
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


# ─── Fix #6: achievements write is atomic ────────────────────────────────────


def test_achievements_save_is_atomic_no_tmp_leak():
    """After save_unlocked, only the real file should remain — no orphan
    .tmp files. Verifies the same tmp+fsync+rename path used by save_world."""
    from content.achievements import save_unlocked

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        save_unlocked("AtomicTester", {"so_say_we_all", "lahey_coded"})
        d = Path(tmp) / "AtomicTester"
        files = sorted(p.name for p in d.iterdir())
        assert files == ["achievements.json"], (
            f"expected exactly achievements.json after save; got {files}"
        )
        # Sanity: the contents survived.
        parsed = json.loads((d / "achievements.json").read_text())
        assert set(parsed) == {"so_say_we_all", "lahey_coded"}


def test_achievements_helper_is_the_shared_atomic_helper():
    """save_unlocked should route through the same engine.save.atomic_write_text
    helper as save_world — the asymmetry the critique flagged was that
    achievements used plain write_text."""
    import inspect
    from content import achievements
    src = inspect.getsource(achievements.save_unlocked)
    assert "atomic_write_text" in src, (
        "save_unlocked should use engine.save.atomic_write_text for durability "
        "parity with save_world; got:\n" + src
    )
    assert ".write_text(" not in src, (
        "save_unlocked should no longer call Path.write_text directly"
    )


# ─── Fix #7: ending-finalize failures go through log_fn ──────────────────────


def test_finalize_ending_logs_epitaph_failure_via_log_fn():
    """A broken epitaph pool should route the exception to log_fn, not vanish."""
    from engine.io import ScriptedIO
    from engine.session import Session
    from engine.world import new_world, set_stat
    from content import epitaphs

    captured = []
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        original = epitaphs.pick_epitaph
        epitaphs.pick_epitaph = lambda _eid: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            world = new_world("LogTester", "env_control")
            world.visited_rooms.append("env_control")
            set_stat(world, "suspicion", 100)  # force spaced ending
            io = ScriptedIO(["salute", "quit"])
            Session(io=io, world=world, log_fn=captured.append).run()
        finally:
            epitaphs.pick_epitaph = original

        joined = "\n".join(captured)
        assert "[finalize-epitaph-error]" in joined, (
            f"expected log_fn to receive epitaph failure; got: {captured}"
        )
        assert "boom" in joined


def test_session_log_fn_default_is_silent_for_local_play():
    """Local play (no log_fn injected) must not crash or print on its own."""
    from engine.io import ScriptedIO
    from engine.session import Session
    from engine.world import new_world

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("DefaultLog", "env_control")
        # No log_fn — should use the silent default
        io = ScriptedIO(["quit"])
        # Just verify it doesn't blow up
        Session(io=io, world=world).run()


# ─── Fix #8: substring matching requires ≥3 chars ────────────────────────────


def test_substring_match_requires_minimum_length():
    """`examine c` previously matched 'ceiling' / 'console' / etc by substring.
    After the fix, queries shorter than 3 chars must match exactly."""
    from engine.commands import _matches

    class Stub:
        def __init__(self, name, aliases):
            self.name = name
            self.aliases = aliases

    bunk = Stub("your bunk", ["bunk", "bed", "rack"])
    locker = Stub("dented locker", ["locker"])

    # 1-char and 2-char substring queries should NO LONGER match by substring
    assert not _matches("b", bunk), "'b' should not substring-match 'your bunk'"
    assert not _matches("lo", locker), "'lo' should not substring-match 'dented locker'"
    # But exact name or exact alias matches at any length still work
    assert _matches("bed", bunk), "exact alias 'bed' should match"
    # 3-char substring matches still work
    assert _matches("bun", bunk), "3-char 'bun' should substring-match 'your bunk'"
    assert _matches("loc", locker), "3-char 'loc' should substring-match 'locker'"


def test_short_canonical_names_still_resolve_via_exact_match():
    """Short canonical names like 'six', 'tigh' etc. should still resolve;
    they hit the exact-name path, not the substring path."""
    from engine.io import ScriptedIO
    from engine.session import Session
    from engine.world import new_world

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        # Tigh is in head_deck_5. His aliases include "tigh" (4 chars).
        world = new_world("ShortQuery", "head_deck_5")
        world.visited_rooms.append("head_deck_5")
        # "tigh" is 4 chars; "examine tigh" should still resolve via alias.
        io = ScriptedIO(["examine tigh", "quit"])
        Session(io=io, world=world).run()
        # The Tigh description should appear (mentions XO or toilet).
        assert "XO" in io.transcript or "toilet" in io.transcript.lower()
