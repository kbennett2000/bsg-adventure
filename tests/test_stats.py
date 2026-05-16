"""Tests for the four hidden stats: MORALE, SUSPICION, CYLON_VIBES, EXHAUSTION."""

import os
import tempfile

import content  # noqa: F401
from engine import events
from engine.io import ScriptedIO
from engine.session import Session
from engine.world import bump_stat, get_stat, new_world, set_stat


def _run(inputs, player_name="StatTester", save_dir=None, start_room="env_control"):
    if save_dir is not None:
        os.environ["BSG_SAVE_DIR"] = save_dir
    world = new_world(player_name, start_room)
    io = ScriptedIO(inputs)
    Session(io=io, world=world).run()
    return io, world


# ─── basic plumbing ────────────────────────────────────────────────────────────


def test_stats_initialize_to_defaults():
    world = new_world("X", "env_control")
    assert world.stats["morale"] == 50
    assert world.stats["suspicion"] == 0
    assert world.stats["cylon_vibes"] == 0
    assert world.stats["exhaustion"] == 0


def test_bump_stat_clamps_to_0_100():
    world = new_world("X", "env_control")
    bump_stat(world, "morale", 200)
    assert world.stats["morale"] == 100
    bump_stat(world, "morale", -500)
    assert world.stats["morale"] == 0
    set_stat(world, "suspicion", 150)
    assert world.stats["suspicion"] == 100


def test_stats_round_trip_through_save_load():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        from engine import save
        world = new_world("Saver", "env_control")
        set_stat(world, "morale", 73)
        set_stat(world, "suspicion", 42)
        set_stat(world, "cylon_vibes", 19)
        set_stat(world, "exhaustion", 88)
        save.save_world(world, slot="default")
        loaded = save.load_world("Saver", "default")
        assert loaded.stats["morale"] == 73
        assert loaded.stats["suspicion"] == 42
        assert loaded.stats["cylon_vibes"] == 19
        assert loaded.stats["exhaustion"] == 88


# ─── status verb ───────────────────────────────────────────────────────────────


def test_status_never_shows_raw_numbers():
    with tempfile.TemporaryDirectory() as tmp:
        io, world = _run(["status", "quit"], save_dir=tmp)
        text = io.transcript
        # No digit-only readouts; we should never leak "morale: 50" or similar.
        # The vibe text might contain "50" coincidentally, so check more specific patterns.
        bad_patterns = ["morale:", "suspicion:", "cylon_vibes:", "exhaustion:", "MORALE", "SUSPICION"]
        for pat in bad_patterns:
            assert pat not in text, f"status leaked stat name '{pat}' to player"


def test_status_high_suspicion_in_character():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("StatTester", "env_control")
        set_stat(world, "suspicion", 90)
        io = ScriptedIO(["status", "quit"])
        Session(io=io, world=world).run()
        assert "Tigh's been watching you" in io.transcript


def test_status_high_cylon_vibes_in_character():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("StatTester", "env_control")
        set_stat(world, "cylon_vibes", 85)
        io = ScriptedIO(["status", "quit"])
        Session(io=io, world=world).run()
        assert "All Along the Watchtower" in io.transcript


def test_status_high_morale_low_exhaustion():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("StatTester", "env_control")
        set_stat(world, "morale", 85)
        set_stat(world, "exhaustion", 10)
        set_stat(world, "suspicion", 5)
        io = ScriptedIO(["status", "quit"])
        Session(io=io, world=world).run()
        assert "frakking unstoppable" in io.transcript


def test_status_does_not_advance_turn():
    with tempfile.TemporaryDirectory() as tmp:
        io, world = _run(["status", "status", "status", "quit"], save_dir=tmp)
        # status is a free verb — turn should stay at 0
        assert world.turn == 0


# ─── stat nudges from world interactions ──────────────────────────────────────


def test_witnessing_tigh_in_head_raises_suspicion():
    with tempfile.TemporaryDirectory() as tmp:
        io, world = _run(["go east", "go east", "quit"], save_dir=tmp)
        # Entering head_deck_5 fires witness_once for tigh_drinking → +10 suspicion
        assert get_stat(world, "suspicion") >= 10, (
            f"witnessing Tigh in stall should bump suspicion; got {world.stats}"
        )


def test_visiting_adamas_quarters_raises_suspicion_a_lot():
    with tempfile.TemporaryDirectory() as tmp:
        io, world = _run(
            [
                "go east", "go north", "go north",  # to corridor_b
                "go up",                              # corridor_a
                "go west",                            # adama's quarters
                "quit",
            ],
            save_dir=tmp,
        )
        # The "unspoken bond" witness is worth +15
        assert get_stat(world, "suspicion") >= 15, world.stats


def test_mopping_drains_morale():
    with tempfile.TemporaryDirectory() as tmp:
        io, world = _run(
            [
                "take mop",
                "use mop",
                "use mop",
                "use mop",
                "quit",
            ],
            save_dir=tmp,
        )
        # Morale starts at 50; three mops → -9
        assert get_stat(world, "morale") <= 50 - 8


def test_drinking_canteen_after_filled_raises_suspicion_and_morale():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Drinker", "env_control")
        world.flags["canteen_filled"] = True
        world.inventory.append("canteen")
        io = ScriptedIO(["drink canteen", "quit"])
        Session(io=io, world=world).run()
        assert get_stat(world, "morale") > 50  # bumped
        assert get_stat(world, "suspicion") >= 8  # drinking on duty


def test_frak_boosts_morale():
    with tempfile.TemporaryDirectory() as tmp:
        # Frak is +1 morale per call after the balance pass.
        io, world = _run(["frak", "frak", "frak", "frak", "frak", "quit"], save_dir=tmp)
        assert get_stat(world, "morale") >= 50 + 4  # five fraks, ~+5


def test_talking_to_hadrian_boosts_morale():
    with tempfile.TemporaryDirectory() as tmp:
        io, world = _run(["talk to hadrian", "talk to hadrian", "quit"], save_dir=tmp)
        assert get_stat(world, "morale") >= 50 + 3


def test_talking_to_adama_drains_morale():
    with tempfile.TemporaryDirectory() as tmp:
        io, world = _run(
            [
                "go east", "go north", "go north", "go up", "go north",  # to CIC
                "talk to adama",
                "quit",
            ],
            save_dir=tmp,
        )
        # Adama drains -2; but other things may have bumped morale up too.
        # Just confirm talking to him registers a downward push (we can't
        # easily isolate the delta without snapshotting around the talk).
        # Use a snapshot approach instead.


def test_talking_to_adama_specifically_drains_morale_via_snapshot():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Snap", "cic")
        # Suppress CIC's first-entry stat side effects so we isolate the Adama delta.
        world.visited_rooms.append("cic")
        world.flags["entered_cic"] = True
        before = get_stat(world, "morale")
        io = ScriptedIO(["talk to adama", "quit"])
        Session(io=io, world=world).run()
        after = get_stat(world, "morale")
        assert after < before, f"adama should drain morale; before={before} after={after}"


def test_six_interaction_bumps_cylon_vibes():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("CylonFan", "corridor_b")
        world.visited_rooms.append("corridor_b")
        before = get_stat(world, "cylon_vibes")
        io = ScriptedIO(["talk to six", "quit"])
        Session(io=io, world=world).run()
        after = get_stat(world, "cylon_vibes")
        assert after - before >= 20, f"six should bump cylon_vibes; before={before} after={after}"


# ─── ending gates by stats ─────────────────────────────────────────────────────


def test_suspicion_100_anywhere_triggers_spaced():
    """At suspicion 100, the session loop forces the spaced ending on next turn."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Doomed", "env_control")
        set_stat(world, "suspicion", 100)
        # Use `salute` to advance a turn — it doesn't touch suspicion. (`wait`
        # was retuned to reduce suspicion, so it would clear the trigger.)
        io = ScriptedIO(["salute", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("__ended__") == "spaced", (
            f"expected spaced via global suspicion; got {world.flags.get('__ended__')!r}"
        )


def test_hero_blocked_by_high_suspicion_routes_to_spaced():
    """Giving Adama the napkin while SUSPICION >= 75 fires a spaced variant, not hero."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Sus", "cic")
        world.visited_rooms.append("cic")
        world.inventory.append("napkin")
        world.flags["realized_napkin_is_coords"] = True
        set_stat(world, "suspicion", 75)
        io = ScriptedIO(["give napkin to adama", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("__ended__") == "spaced"
        assert "DIDN'T TRUST YOU" in io.transcript


def test_hero_still_fires_with_low_suspicion():
    """The normal hero path still works when stats stay clean."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Clean", "cic")
        world.visited_rooms.append("cic")
        world.inventory.append("napkin")
        world.flags["realized_napkin_is_coords"] = True
        # Low suspicion, low exhaustion — hero should fire
        io = ScriptedIO(["give napkin to adama", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("__ended__") == "hero"


def test_cylon_ending_gated_on_cylon_vibes_threshold():
    """At CYLON_VIBES >= 75, the next Six talk triggers the love triangle."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Devotee", "corridor_b")
        world.visited_rooms.append("corridor_b")
        set_stat(world, "cylon_vibes", 80)
        io = ScriptedIO(["talk to six", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("__ended__") == "cylon_love_triangle"


def test_three_sensitive_topics_to_tigh_still_spaces():
    """Backwards compat: the old test_spaced_ending_via_tigh_suspicion path
    should still work, now via global suspicion."""
    with tempfile.TemporaryDirectory() as tmp:
        io, world = _run(
            [
                "go east", "go east",
                "talk to tigh",                  # quest
                "talk to tigh about adama",      # +25
                "talk to tigh about flask",      # +25
                "talk to tigh about bill",       # +25 → 75 (plus head witness +10 = 85)
                "talk to tigh",
            ],
            save_dir=tmp,
        )
        assert world.flags.get("__ended__") == "spaced"


# ─── exhaustion mechanics ─────────────────────────────────────────────────────


def test_exhaustion_ticks_up_each_turn():
    with tempfile.TemporaryDirectory() as tmp:
        io, world = _run(["wait", "wait", "wait", "wait", "wait", "quit"], save_dir=tmp)
        # 5 turns × 1 exhaustion per turn
        assert get_stat(world, "exhaustion") == 5


def test_exhaustion_100_collapses_to_sickbay():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Tired", "env_control")
        world.visited_rooms.append("env_control")
        world.inventory.append("canteen")
        world.inventory.append("mop")
        set_stat(world, "exhaustion", 99)
        io = ScriptedIO(["wait", "quit"])
        Session(io=io, world=world).run()
        assert world.current_room == "sickbay"
        # canteen and mop should be lost to "you have suspicions"
        assert "canteen" not in world.inventory
        assert "mop" not in world.inventory
        # exhaustion gets reset to a tired-but-functional baseline (30); quit doesn't tick.
        assert get_stat(world, "exhaustion") == 30


def test_collapse_preserves_napkin():
    """The macguffin survives a collapse — the player has a death-grip on it."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Tired", "env_control")
        world.visited_rooms.append("env_control")
        world.inventory.append("napkin")
        world.inventory.append("canteen")
        set_stat(world, "exhaustion", 99)
        io = ScriptedIO(["wait", "quit"])
        Session(io=io, world=world).run()
        assert "napkin" in world.inventory
        assert "canteen" not in world.inventory


def test_exhaustion_high_adds_loopy_description_modifier():
    """At exhaustion >= 50, room descriptions get a loopy suffix."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Sleepy", "env_control")
        world.visited_rooms.append("env_control")
        set_stat(world, "exhaustion", 55)
        io = ScriptedIO(["look", "quit"])
        Session(io=io, world=world).run()
        # The loopy modifier should appear in the body somewhere
        assert "blink" in io.transcript.lower() or "edges of everything" in io.transcript.lower()


def test_exhaustion_very_high_adds_phantom_npc():
    """At exhaustion >= 80, room renders include a phantom in the present list."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Hallucinating", "env_control")
        world.visited_rooms.append("env_control")
        set_stat(world, "exhaustion", 85)
        io = ScriptedIO(["look", "quit"])
        Session(io=io, world=world).run()
        # A phantom from the list should appear in the "Present:" line
        phantom_signals = ["wrong number of fingers", "facing the corner", "without teeth", "yourself, except shorter"]
        assert any(p in io.transcript for p in phantom_signals), (
            f"expected phantom in description; got transcript tail:\n{io.transcript[-1500:]}"
        )


# ─── high cylon vibes shapes descriptions ──────────────────────────────────────


def test_high_cylon_vibes_adds_song_in_head():
    """At cylon_vibes >= 60, descriptions mention the song stuck in the head."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Hearing", "env_control")
        world.visited_rooms.append("env_control")
        set_stat(world, "cylon_vibes", 65)
        io = ScriptedIO(["look", "quit"])
        Session(io=io, world=world).run()
        assert "song" in io.transcript.lower() and "head" in io.transcript.lower()


def test_high_suspicion_adds_watched_feeling():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Paranoid", "env_control")
        world.visited_rooms.append("env_control")
        set_stat(world, "suspicion", 80)
        io = ScriptedIO(["look", "quit"])
        Session(io=io, world=world).run()
        assert "watched" in io.transcript.lower()
