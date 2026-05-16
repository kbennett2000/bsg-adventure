"""Tests for the watch-cycle time system, NPC schedules, hunger mechanic,
duty roster, and time-gated quests."""

import os
import tempfile

import content  # noqa: F401
from engine.io import ScriptedIO
from engine.session import Session
from engine.world import (
    SHIFT_COUNT,
    SHIFT_NAMES,
    TURNS_PER_SHIFT,
    advance_shift,
    bump_stat,
    get_stat,
    new_world,
    set_stat,
)


# Indices we hard-code in tests for clarity.
MORNING_WATCH = 0
FORENOON = 1
AFTERNOON = 2
DOG_WATCH = 3
NIGHT = 4


# ─── time advancement ─────────────────────────────────────────────────────────


def test_shift_count_is_five():
    assert SHIFT_COUNT == 5
    assert SHIFT_NAMES == [
        "Morning Watch", "Forenoon", "Afternoon", "Dog Watch", "Night",
    ]


def test_shift_auto_advances_every_turns_per_shift():
    """Walking around long enough auto-advances the watch."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Tester", "env_control")
        world.visited_rooms.append("env_control")
        # Run TURNS_PER_SHIFT turn-advancing actions.
        cmds = ["salute"] * TURNS_PER_SHIFT + ["quit"]
        io = ScriptedIO(cmds)
        Session(io=io, world=world).run()
        assert world.shift == FORENOON, (
            f"after {TURNS_PER_SHIFT} turns, expected shift=Forenoon (1); got {world.shift}"
        )


def test_day_rolls_over_after_full_cycle():
    """After SHIFT_COUNT shifts of advancing, day += 1."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Wrapper", "env_control")
        assert world.day == 1
        advance_shift(world, SHIFT_COUNT)
        assert world.day == 2
        assert world.shift == MORNING_WATCH


def test_sleep_verb_advances_one_shift_and_resets_exhaustion():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Sleeper", "env_control")
        world.visited_rooms.append("env_control")
        set_stat(world, "exhaustion", 60)
        starting_shift = world.shift
        io = ScriptedIO(["sleep", "quit"])
        Session(io=io, world=world).run()
        assert world.shift == (starting_shift + 1) % SHIFT_COUNT
        assert get_stat(world, "exhaustion") <= 1, (
            f"sleep should reset exhaustion ~0; got {get_stat(world, 'exhaustion')}"
        )


def test_sleep_through_full_day_returns_to_morning_watch():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("FullCycle", "env_control")
        world.visited_rooms.append("env_control")
        io = ScriptedIO(["sleep", "sleep", "sleep", "sleep", "sleep", "quit"])
        Session(io=io, world=world).run()
        assert world.shift == MORNING_WATCH
        assert world.day == 2


def test_status_reports_current_shift():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Clock", "env_control")
        world.visited_rooms.append("env_control")
        world.shift = AFTERNOON
        io = ScriptedIO(["status", "quit"])
        Session(io=io, world=world).run()
        assert "Afternoon" in io.transcript
        assert "day 1" in io.transcript.lower() or "Day 1" in io.transcript


# ─── NPC schedules ────────────────────────────────────────────────────────────


def test_adama_in_cic_during_forenoon():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("CICVisitor", "cic")
        world.visited_rooms.append("cic")
        world.flags["entered_cic"] = True  # suppress on-enter narrative
        world.shift = FORENOON
        io = ScriptedIO(["look", "quit"])
        Session(io=io, world=world).run()
        assert "Admiral Adama" in io.transcript


def test_adama_not_in_cic_at_night():
    """At Night, Adama is in his quarters, not CIC."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("NightVisitor", "cic")
        world.visited_rooms.append("cic")
        world.flags["entered_cic"] = True
        world.shift = NIGHT
        io = ScriptedIO(["look", "quit"])
        Session(io=io, world=world).run()
        # The "Present:" line should not include Adama at Night.
        # Long_desc may mention him as static scenery — that's narrative, not
        # the dynamic presence list. We extract just the Present: line(s).
        present_lines = []
        for out in io.outputs:
            for line in out.split("\n"):
                if line.startswith("Present:"):
                    present_lines.append(line)
        assert present_lines, "expected a Present: line in CIC"
        assert all("Admiral Adama" not in ln for ln in present_lines), (
            f"Adama should not be in CIC's Present: line at Night; got:\n{present_lines}"
        )


def test_adama_in_quarters_at_night():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Night", "adamas_quarters")
        world.visited_rooms.append("adamas_quarters")
        world.flags["entered_adamas_quarters"] = True
        world.shift = NIGHT
        io = ScriptedIO(["look", "quit"])
        Session(io=io, world=world).run()
        assert "Admiral Adama" in io.transcript


def test_starbuck_in_brig_at_night():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("BrigGoer", "brig")
        world.visited_rooms.append("brig")
        world.flags["entered_brig"] = True
        world.shift = NIGHT
        io = ScriptedIO(["look", "quit"])
        Session(io=io, world=world).run()
        assert "Lieutenant Thrace" in io.transcript


def test_starbuck_in_rec_during_afternoon():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Afternoon", "pilots_rec")
        world.visited_rooms.append("pilots_rec")
        world.flags["entered_pilots_rec"] = True
        world.shift = AFTERNOON
        io = ScriptedIO(["look", "quit"])
        Session(io=io, world=world).run()
        assert "Lieutenant Thrace" in io.transcript


def test_baltar_always_in_lab():
    """Baltar's schedule is 'every shift → lab.' He's there at any hour."""
    for shift in range(SHIFT_COUNT):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["BSG_SAVE_DIR"] = tmp
            world = new_world("Lab", "baltars_lab")
            world.visited_rooms.append("baltars_lab")
            world.flags["entered_baltars_lab"] = True
            world.shift = shift
            io = ScriptedIO(["look", "quit"])
            Session(io=io, world=world).run()
            assert "Doctor Baltar" in io.transcript, (
                f"Baltar should be in his lab at shift {SHIFT_NAMES[shift]}"
            )


def test_tigh_always_in_head():
    """Tigh's schedule is 'every shift → head_deck_5.' He's there at any hour."""
    for shift in range(SHIFT_COUNT):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["BSG_SAVE_DIR"] = tmp
            world = new_world("Head", "head_deck_5")
            world.visited_rooms.append("head_deck_5")
            world.flags["entered_head"] = True
            world.shift = shift
            io = ScriptedIO(["look", "quit"])
            Session(io=io, world=world).run()
            assert "Colonel Tigh" in io.transcript


# ─── hunger / mess open hours ─────────────────────────────────────────────────


def test_mess_open_morning_and_afternoon_only():
    """Mess closure is reflected in the entry narrative."""
    # Closed at Forenoon, Dog Watch, Night.
    for shift in (FORENOON, DOG_WATCH, NIGHT):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["BSG_SAVE_DIR"] = tmp
            world = new_world("Hungry", "mess_hall")
            world.visited_rooms.append("mess_hall")
            world.flags["seen_mess_hall_jump_gossip"] = True  # skip first-visit narrative
            world.shift = shift
            io = ScriptedIO(["look", "quit"])
            Session(io=io, world=world).run()
            assert "closed" in io.transcript.lower() or "shuttered" in io.transcript.lower()


def test_eat_tray_when_mess_is_closed_says_so():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Hungry", "mess_hall")
        world.visited_rooms.append("mess_hall")
        world.shift = NIGHT
        io = ScriptedIO(["eat tray", "quit"])
        Session(io=io, world=world).run()
        assert "no food" in io.transcript.lower() or "closed" in io.transcript.lower()
        assert not world.flags.get("ate_today")


def test_eat_tray_when_mess_open_sets_ate_today():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Diner", "mess_hall")
        world.visited_rooms.append("mess_hall")
        world.shift = MORNING_WATCH
        io = ScriptedIO(["eat tray", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("ate_today") is True


def test_skipping_meal_costs_exhaustion_at_day_rollover():
    """Sleep through the full day without eating → exhaustion +5 next morning."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Faster", "env_control")
        world.visited_rooms.append("env_control")
        set_stat(world, "exhaustion", 10)
        # Sleep through the full day: 5 sleeps → wrap to Morning Watch (day 2)
        io = ScriptedIO(["sleep"] * 5 + ["quit"])
        Session(io=io, world=world).run()
        # Day should have rolled over; exhaustion penalty applied.
        assert world.day == 2
        # Exhaustion is reset to 0 on each sleep, but the penalty fires AFTER
        # rollover; final exhaustion = 0 (last sleep) + penalty applied AFTER.
        # The penalty fires from on_shift_change at day boundary.
        assert get_stat(world, "exhaustion") >= 5


# ─── duty roster ──────────────────────────────────────────────────────────────


def test_examining_roster_in_corridor_c12_shows_today_duty():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("DutyReader", "corridor_c12")
        world.visited_rooms.append("corridor_c12")
        io = ScriptedIO(["examine roster", "quit"])
        Session(io=io, world=world).run()
        assert "DAILY DUTY ROSTER" in io.transcript
        assert "Day 1" in io.transcript
        # One of the chore lines should be visible.
        t = io.transcript
        chore_lines = ["MOP THE FRAKKIN'", "REROUTE COOLANT", "STANDBY ESCORT", '"ASSIST" DR. BALTAR']
        assert any(c in t for c in chore_lines), (
            f"expected one chore in the roster; got:\n{t}"
        )


def test_duty_is_deterministic_per_day_and_player():
    """A given (day, player_name) always produces the same duty assignment."""
    from content.duties import current_duty
    w1 = new_world("Alice", "env_control")
    w2 = new_world("Alice", "env_control")
    assert current_duty(w1) == current_duty(w2)
    # Different name → potentially different (sometimes equal — they share
    # a 4-element pool, so this isn't a strict guarantee, but the SAME
    # player on the SAME day must be identical):
    w3 = new_world("Alice", "env_control")
    w3.day = 1
    assert current_duty(w3) == current_duty(w1)


def test_completing_assigned_duty_reduces_suspicion():
    """The chore is boring (morale -3) but exonerating (suspicion -5)."""
    from content.duties import current_duty
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        # Force today's duty to be the easy-to-complete 'reroute_coolant'.
        world = new_world("Worker", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["duty_today"] = "reroute_coolant"
        set_stat(world, "suspicion", 30)
        before_s = get_stat(world, "suspicion")
        io = ScriptedIO(["use console", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("duty_console_today") is True
        assert get_stat(world, "suspicion") < before_s


def test_skipping_duty_raises_suspicion_at_day_rollover():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Skipper", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["duty_today"] = "mop_the_head"   # won't be done
        before_s = get_stat(world, "suspicion")
        io = ScriptedIO(["sleep"] * 5 + ["quit"])    # full day to rollover
        Session(io=io, world=world).run()
        assert world.day == 2
        # Suspicion bumped from the missed duty (+5) and possibly from hunger
        # narrative (no suspicion bump from hunger itself, only exhaustion).
        assert get_stat(world, "suspicion") >= before_s + 5


# ─── time-gated quests ───────────────────────────────────────────────────────


def test_stash_loose_tile_not_findable_in_daytime():
    """Outside Night, the loose tile examine shouldn't reveal the flask."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("DayThief", "head_deck_5")
        world.visited_rooms.append("head_deck_5")
        world.flags["entered_head"] = True
        world.shift = MORNING_WATCH
        io = ScriptedIO(["examine loose tile", "quit"])
        Session(io=io, world=world).run()
        assert not world.flags.get("found_flask")
        assert "flask" not in world.inventory


def test_stash_loose_tile_findable_at_night():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("NightThief", "head_deck_5")
        world.visited_rooms.append("head_deck_5")
        world.flags["entered_head"] = True
        world.shift = NIGHT
        io = ScriptedIO(["examine loose tile", "take flask", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("found_flask") is True
        assert "flask" in world.inventory


def test_cards_quest_locked_outside_afternoon():
    """Talking to Starbuck about cards at Morning Watch should NOT start the quest."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("EarlyBird", "pilots_rec")
        world.visited_rooms.append("pilots_rec")
        world.flags["entered_pilots_rec"] = True
        world.shift = MORNING_WATCH
        io = ScriptedIO(["talk to starbuck about cards", "quit"])
        Session(io=io, world=world).run()
        assert not world.flags.get("quest_cards_started")
        # The in-character deflection mentions afternoons
        assert "afternoon" in io.transcript.lower()


def test_cards_quest_unlocked_during_afternoon():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("OnTime", "pilots_rec")
        world.visited_rooms.append("pilots_rec")
        world.flags["entered_pilots_rec"] = True
        world.shift = AFTERNOON
        io = ScriptedIO(["talk to starbuck about cards", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("quest_cards_started") is True


# ─── discoverability via gossip ──────────────────────────────────────────────


def test_hadrian_explains_stash_is_night_only():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Curious", "env_control")
        world.visited_rooms.append("env_control")
        io = ScriptedIO(["talk to hadrian about stash", "quit"])
        Session(io=io, world=world).run()
        assert "night" in io.transcript.lower()


def test_hadrian_explains_cards_is_afternoon():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Curious", "env_control")
        world.visited_rooms.append("env_control")
        io = ScriptedIO(["talk to hadrian about cards", "quit"])
        Session(io=io, world=world).run()
        assert "afternoon" in io.transcript.lower()


def test_cook_explains_mess_hours():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Hungry", "mess_hall")
        world.visited_rooms.append("mess_hall")
        world.shift = MORNING_WATCH  # Cook is here
        io = ScriptedIO(["talk to cook about hours", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        assert "morning" in t and "afternoon" in t


def test_cottle_explains_sleep_mechanic():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Confused", "sickbay")
        world.visited_rooms.append("sickbay")
        io = ScriptedIO(["talk to cottle about sleep", "quit"])
        Session(io=io, world=world).run()
        assert "sleep" in io.transcript.lower()
        assert "advances time" in io.transcript.lower() or "watch clock" in io.transcript.lower()


# ─── round-trip the new fields ────────────────────────────────────────────────


def test_shift_day_turns_round_trip():
    from engine import save as save_module
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("RT", "env_control")
        world.shift = DOG_WATCH
        world.day = 7
        world.turns_this_shift = 9
        save_module.save_world(world, slot="default")
        loaded = save_module.load_world("RT", "default")
        assert loaded.shift == DOG_WATCH
        assert loaded.day == 7
        assert loaded.turns_this_shift == 9
