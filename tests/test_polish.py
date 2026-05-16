"""Tests for the polish pass: ambient pool size, epitaphs, achievements,
new-game-plus, and the densest 'have we met?' deja-vu lines."""

import json
import os
import tempfile

import content  # noqa: F401
from engine import events
from engine.io import ScriptedIO
from engine.session import Session
from engine.world import bump_stat, get_stat, new_world, set_stat


def _run(inputs, player_name="PolishTester", save_dir=None, start_room="env_control"):
    if save_dir is not None:
        os.environ["BSG_SAVE_DIR"] = save_dir
    world = new_world(player_name, start_room)
    io = ScriptedIO(inputs)
    next_action = Session(io=io, world=world).run()
    return io, world, next_action


# ─── Ambient pool ─────────────────────────────────────────────────────────────


def test_ambient_pool_is_at_least_25():
    """The ambient registration list should hold ~25 entries."""
    # events._REGISTERED is the registry from engine.events
    assert len(events._REGISTERED) >= 25, (
        f"expected at least 25 ambient events, got {len(events._REGISTERED)}"
    )


def test_ambient_includes_user_specified_lines():
    """The four user-requested ambient lines should be present."""
    pool = [s for s in events._REGISTERED if isinstance(s, str)]
    assert any("brown duffel" in s.lower() for s in pool)
    assert any("definitely talking about adama" in s.lower() for s in pool)
    assert any("baltar is laughing at his own joke" in s.lower() for s in pool)
    assert any("you will hear it again" in s.lower() for s in pool)


# ─── Death messages / epitaphs ───────────────────────────────────────────────


def test_epitaph_count_at_least_15():
    """At least 15 unique epitaphs across all ending pools."""
    from content.epitaphs import EPITAPHS
    total = sum(len(pool) for pool in EPITAPHS.values())
    assert total >= 15, f"expected ≥15 epitaphs, got {total}"


def test_spaced_epitaph_pool_includes_no_one_remembers():
    """The spaced ending pool must contain the 'no one will remember your name' line."""
    from content.epitaphs import EPITAPHS
    spaced = " ".join(EPITAPHS["spaced"]).lower()
    assert "nobody will remember your name" in spaced or "no one will remember your name" in spaced


def test_spaced_ending_appends_an_epitaph():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Doomed", "env_control")
        world.visited_rooms.append("env_control")
        set_stat(world, "suspicion", 100)
        io = ScriptedIO(["wait", "quit"])
        Session(io=io, world=world).run()
        # The ending text + an epitaph + the END marker should all appear.
        t = io.transcript
        assert "── ENDING:" in t
        assert "── END ──" in t
        # An epitaph from the spaced pool should appear somewhere in the transcript.
        # Match on any of the spaced pool lines.
        from content.epitaphs import EPITAPHS
        epitaph_found = any(
            line[:30] in t for line in EPITAPHS["spaced"]
        )
        assert epitaph_found, "expected one of the spaced epitaphs in transcript"


# ─── Achievements ────────────────────────────────────────────────────────────


def test_so_say_we_all_unlocks_at_50_fraks():
    """50 frak invocations unlock the achievement on next ending."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Frakker", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["__frak_index__"] = 50  # already hit 50
        set_stat(world, "suspicion", 100)  # force spaced
        io = ScriptedIO(["wait", "quit"])
        Session(io=io, world=world).run()
        assert "So Say We All" in io.transcript


def test_promotion_material_unlocks_on_zero_suspicion_hero():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Cleaner", "cic")
        world.visited_rooms.append("cic")
        world.inventory.append("napkin")
        world.flags["realized_napkin_is_coords"] = True
        world.flags["entered_cic"] = True  # skip the +3 sus from CIC entry
        # Make sure suspicion is exactly 0
        set_stat(world, "suspicion", 0)
        io = ScriptedIO(["give napkin to adama", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("__ended__") == "hero"
        assert "Promotion Material" in io.transcript


def test_lahey_coded_unlocks_after_five_drinks():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Drinker", "env_control")
        world.visited_rooms.append("env_control")
        world.inventory.append("flask")
        # Drink 5 times then trigger an ending
        world.flags["tigh_drink_count"] = 5
        set_stat(world, "suspicion", 100)
        io = ScriptedIO(["wait", "quit"])
        Session(io=io, world=world).run()
        assert "Lahey-coded" in io.transcript


def test_achievements_persist_to_disk():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Saver", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["__frak_index__"] = 50
        set_stat(world, "suspicion", 100)
        io = ScriptedIO(["wait", "quit"])
        Session(io=io, world=world).run()
        # File should be written
        from pathlib import Path
        ach_path = Path(tmp) / "Saver" / "achievements.json"
        assert ach_path.exists()
        data = json.loads(ach_path.read_text())
        assert "so_say_we_all" in data


def test_achievements_do_not_double_unlock():
    """Loading and unlocking again should not duplicate."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        from content.achievements import load_unlocked, save_unlocked, check_and_unlock
        save_unlocked("Tester", {"so_say_we_all"})
        # Build a world that would normally unlock so_say_we_all
        world = new_world("Tester", "env_control")
        world.flags["__frak_index__"] = 50
        world.flags["__ended__"] = "spaced"
        new = check_and_unlock(world)
        # Already-unlocked achievements should not reappear in the new list
        assert all(a["id"] != "so_say_we_all" for a in new)


# ─── New game plus ───────────────────────────────────────────────────────────


def test_session_returns_ng_plus_dict_when_player_answers_yes():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Repeater", "env_control")
        world.visited_rooms.append("env_control")
        set_stat(world, "suspicion", 100)  # force spaced
        # After ending: prompt is shown, we answer "y"
        io = ScriptedIO(["wait", "y"])
        next_action = Session(io=io, world=world).run()
        assert next_action is not None
        assert next_action["ng_plus"] is True
        assert next_action["previous_ending"] == "spaced"
        assert next_action["ng_plus_count"] == 1


def test_session_returns_none_when_player_declines_ng_plus():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("OneAndDone", "env_control")
        world.visited_rooms.append("env_control")
        set_stat(world, "suspicion", 100)
        io = ScriptedIO(["wait", "n"])
        next_action = Session(io=io, world=world).run()
        assert next_action is None


def test_ng_plus_count_increments_across_runs():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Recurring", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["ng_plus_count"] = 3  # this is the 4th run
        set_stat(world, "suspicion", 100)
        io = ScriptedIO(["wait", "y"])
        next_action = Session(io=io, world=world).run()
        assert next_action["ng_plus_count"] == 4


def test_hadrian_deja_vu_on_ng_plus():
    """In NG+, Hadrian's first default talk includes a déjà vu prefix."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Returnee", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["ng_plus"] = True
        io = ScriptedIO(["talk to hadrian", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        assert "done this before" in t or "have we" in t or "exact conversation" in t


def test_adama_deja_vu_on_ng_plus():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Returnee", "cic")
        world.visited_rooms.append("cic")
        world.flags["entered_cic"] = True
        world.flags["ng_plus"] = True
        io = ScriptedIO(["talk to adama", "quit"])
        Session(io=io, world=world).run()
        assert "conferred" in io.transcript


def test_six_deja_vu_on_ng_plus():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Returnee", "corridor_b")
        world.visited_rooms.append("corridor_b")
        world.flags["ng_plus"] = True
        io = ScriptedIO(["talk to six", "quit"])
        Session(io=io, world=world).run()
        assert "knew you would come back" in io.transcript.lower()


def test_normal_run_does_not_show_deja_vu():
    """Without ng_plus flag, no déjà vu prefix appears."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Newbie", "env_control")
        world.visited_rooms.append("env_control")
        io = ScriptedIO(["talk to hadrian", "quit"])
        Session(io=io, world=world).run()
        assert "done this before" not in io.transcript.lower()
        assert "exact conversation" not in io.transcript.lower()


def test_all_of_this_has_happened_before_achievement():
    """Finishing an ending while ng_plus flag is set unlocks the NG+ achievement."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Wheel", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["ng_plus"] = True
        set_stat(world, "suspicion", 100)
        io = ScriptedIO(["wait", "n"])
        Session(io=io, world=world).run()
        assert "All of This Has Happened Before" in io.transcript


# ─── Title screen ────────────────────────────────────────────────────────────


def test_subtitles_pool_has_at_least_10():
    from main import SUBTITLES
    assert len(SUBTITLES) >= 10


def test_subtitles_include_user_requested_examples():
    from main import SUBTITLES
    assert any("mopping in space" in s.lower() for s in SUBTITLES)
    assert any("40%" in s for s in SUBTITLES)
    assert any("doesn't know your name" in s.lower() for s in SUBTITLES)


# ─── Room density ────────────────────────────────────────────────────────────


def test_every_room_longdesc_has_at_least_two_sentences_of_detail():
    """The polish pass should leave every room with a substantial description."""
    from engine.registry import ROOMS
    for room_id, room in ROOMS.items():
        sentence_count = room.long_desc.count(".") + room.long_desc.count("!")
        assert sentence_count >= 4, (
            f"room {room_id} has only {sentence_count} sentences; "
            f"polish pass should leave each room with denser detail"
        )
