"""Regression tests for the second code critique (six issues).

Each test corresponds to one of the six fixes in the second critique pass:
  1) `wait` at suspicion=100 must still kill you (death check not bypassed
     by a same-turn stat-decrementing verb).
  2) Press conference resume — a session resumed mid-conference must
     re-render the current question, not just the room description.
  3) Multi-day rollover must apply ONE penalty per missed day (not collapse
     them all into a single hit).
  4) README test count is no longer hardcoded.
  5) `_question_rng` docstring acknowledges save-scum determinism.
  6) `cmd_sleep` does NOT reach into Session._on_shift_change — it routes
     through HandlerResult.shift_advanced.
"""

import os
import tempfile

import content  # noqa: F401 — registers world content
from content import duties, press
from engine import commands
from engine.commands import HandlerResult
from engine.io import ScriptedIO
from engine.session import Session
from engine.world import bump_stat, get_stat, new_world, set_stat


# ─── Bug 1: wait at suspicion=100 must trigger spaced ────────────────────────


def test_wait_at_suspicion_100_still_triggers_spaced():
    """Before the fix: cmd_wait bumped suspicion -1 BEFORE the death check,
    so a player at 100 could wait indefinitely, drifting back to 95. After
    the fix: the top-of-loop death check fires the ending the moment the
    loop re-enters, regardless of what the player typed."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("WaitToDie", "env_control")
        world.visited_rooms.append("env_control")
        # Pre-set suspicion to 99, then bump to 100 via a stat helper so the
        # *next* loop iteration's top-of-loop death check is what fires.
        set_stat(world, "suspicion", 99)
        bump_stat(world, "suspicion", 1)  # → 100
        assert get_stat(world, "suspicion") == 100

        # Try to escape with `wait`. Old bug: 5 waits would drift sus to 95.
        # New behavior: top-of-loop check fires spaced BEFORE the wait runs.
        io = ScriptedIO(["wait", "wait", "wait", "wait", "wait", "n"])
        Session(io=io, world=world).run()
        assert world.flags.get("__ended__") == "spaced", (
            f"expected spaced ending, got {world.flags.get('__ended__')!r}; "
            f"suspicion is now {get_stat(world, 'suspicion')}"
        )


def test_wait_can_still_lower_sub_threshold_suspicion():
    """Sanity check: the fix doesn't break the normal `wait` behavior.
    At sus=50, `wait` still reduces it."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("WaitToCool", "env_control")
        world.visited_rooms.append("env_control")
        set_stat(world, "suspicion", 50)
        io = ScriptedIO(["wait", "quit"])
        Session(io=io, world=world).run()
        assert get_stat(world, "suspicion") == 49


def test_status_at_suspicion_100_fires_spaced():
    """Non-advancing verbs (status, inventory) still trigger the ending
    when sus is at 100 — the death check runs whether or not the turn
    advanced."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("StatusReader", "env_control")
        world.visited_rooms.append("env_control")
        set_stat(world, "suspicion", 100)
        io = ScriptedIO(["n"])  # entry fires it; we decline NG+
        Session(io=io, world=world).run()
        assert world.flags.get("__ended__") == "spaced"


# ─── Bug 2: press conference resume re-renders the current question ──────────


def test_resumed_press_conference_re_prompts_question():
    """Save mid-conference → load → the player should see the current
    question on entry, NOT just the room description."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("PressResume", "sickbay")
        world.visited_rooms.append("sickbay")
        # Manually construct a mid-conference state — what a save would
        # have captured. press_round=2 means we're on the 3rd question.
        world.flags["press_active"] = True
        world.flags["press_round"] = 2
        world.flags["press_questions"] = [q["id"] for q in press.QUESTIONS]
        world.flags["press_credibility"] = 50

        io = ScriptedIO(["quit"])  # immediately quit; we just want the entry render
        Session(io=io, world=world).run()

        transcript = io.transcript
        # The current question text (cylons_among_us, round 3) must appear.
        assert "Round 3 of 6" in transcript, (
            "expected the resumed press question to be rendered on entry;\n"
            f"transcript was:\n{transcript[:1000]}"
        )
        # The question's prose must also be present.
        assert "Cylon" in transcript


def test_render_current_question_returns_empty_when_press_inactive():
    """The public helper safely returns '' when there is no active conference."""
    world = new_world("Dormant", "env_control")
    assert press.render_current_question(world) == ""


def test_render_current_question_returns_question_text_mid_conference():
    """Direct call to the public helper produces the expected prompt."""
    world = new_world("MidConf", "sickbay")
    world.flags["press_active"] = True
    world.flags["press_round"] = 0
    world.flags["press_questions"] = [q["id"] for q in press.QUESTIONS]
    text = press.render_current_question(world)
    assert "Round 1 of 6" in text
    assert "honest, political, or unhinged" in text


# ─── Bug 3: multi-day rollover applies per-day penalties ─────────────────────


def test_three_day_jump_applies_three_duty_penalties():
    """If three days pass between rollovers, the player loses 3 × duty
    suspicion (15), not just 5."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("CalendarJumper", "env_control")
        world.flags["_last_rollover_day"] = 1
        world.flags["_first_shift_change_done"] = True
        world.day = 4   # three days jumped
        # Assign yesterday's duty so the duty-skip branch is exercised.
        world.flags["duty_today"] = "mop_the_head"
        # Don't mark it done; don't mark ate_today.
        set_stat(world, "suspicion", 0)
        set_stat(world, "exhaustion", 0)
        duties.on_shift_change(world)
        # 3 missed days × 5 sus per day = 15
        assert get_stat(world, "suspicion") == 15, (
            f"expected sus=15 after 3-day jump, got {get_stat(world, 'suspicion')}"
        )
        # 3 missed days × 6 exhaustion per day = 18
        assert get_stat(world, "exhaustion") == 18, (
            f"expected exh=18 after 3-day jump, got {get_stat(world, 'exhaustion')}"
        )


def test_one_day_jump_still_applies_single_penalty():
    """The single-day case is unchanged: one duty skip = 5 sus, one missed
    meal = 6 exhaustion."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("OneDay", "env_control")
        world.flags["_last_rollover_day"] = 1
        world.flags["_first_shift_change_done"] = True
        world.day = 2
        world.flags["duty_today"] = "mop_the_head"
        set_stat(world, "suspicion", 0)
        set_stat(world, "exhaustion", 0)
        duties.on_shift_change(world)
        assert get_stat(world, "suspicion") == 5
        assert get_stat(world, "exhaustion") == 6


def test_completed_duty_avoids_duty_penalty_even_on_multi_day_jump():
    """If the most recent day's duty IS done, day 1 contributes no duty
    penalty — but later missed days still do (the player wasn't conscious
    for them)."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("MoppedThenJumped", "env_control")
        world.flags["_last_rollover_day"] = 1
        world.flags["_first_shift_change_done"] = True
        world.day = 4   # 3-day jump
        world.flags["duty_today"] = "mop_the_head"
        world.flags["duty_mopped_today"] = True   # mopped on day 1
        world.flags["ate_today"] = True            # also ate on day 1
        set_stat(world, "suspicion", 0)
        set_stat(world, "exhaustion", 0)
        duties.on_shift_change(world)
        # 2 missed days × 5 sus = 10  (day 1's duty was done)
        assert get_stat(world, "suspicion") == 10
        # 2 missed days × 6 exh = 12  (day 1's meal was eaten)
        assert get_stat(world, "exhaustion") == 12


# ─── Bug 5: _question_rng docstring acknowledges save-scum determinism ───────


def test_question_rng_docstring_mentions_save_scum():
    """The deterministic seed is load-bearing; the docstring must say so."""
    doc = press._question_rng.__doc__ or ""
    assert "save-scum" in doc.lower() or "save scum" in doc.lower(), (
        "_question_rng docstring should explain that the deterministic seed "
        "is also a save-scumming defense, not just for test predictability."
    )


def test_question_rng_is_actually_deterministic_per_savestate():
    """Same world state → same RNG → same first roll. This is what the
    docstring is documenting; verify the contract still holds."""
    world = new_world("Scummer", "sickbay")
    world.day = 3
    r1 = press._question_rng(world, "election")
    r2 = press._question_rng(world, "election")
    assert r1.choice([1, 2, 3, 4, 5]) == r2.choice([1, 2, 3, 4, 5])


# ─── Bug 6: cmd_sleep routes shift change via HandlerResult.shift_advanced ───


def test_handler_result_has_shift_advanced_field():
    """The new field exists with the documented default."""
    r = HandlerResult()
    assert hasattr(r, "shift_advanced")
    assert r.shift_advanced is False


def test_cmd_sleep_returns_shift_advanced_true():
    """cmd_sleep no longer touches session internals — it sets the flag and
    lets the loop run _on_shift_change."""
    world = new_world("Sleeper", "env_control")
    from engine.parser import parse
    cmd = parse("sleep")
    # session=None must work without exceptions (this used to be a try/except
    # AttributeError reach-in).
    result = commands.cmd_sleep(world, cmd, session=None)
    assert result.shift_advanced is True
    assert result.advance_turn is False


def test_cmd_sleep_does_not_call_session_internals():
    """The handler must not depend on session having any private methods.
    A stand-in object with no _on_shift_change should still work."""
    world = new_world("Sleeper2", "env_control")
    from engine.parser import parse
    cmd = parse("sleep")

    class BareSession:
        pass

    result = commands.cmd_sleep(world, cmd, session=BareSession())
    assert result.shift_advanced is True


def test_sleep_through_session_loop_fires_shift_change_banner():
    """End-to-end: `sleep` in the loop fires the shift-change banner via
    the new shift_advanced routing. We start on Morning Watch (shift 0);
    after one `sleep` we should see the Forenoon banner."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("SleepingPilot", "env_control")
        world.visited_rooms.append("env_control")
        assert world.shift == 0  # start on Morning Watch
        io = ScriptedIO(["sleep", "quit"])
        Session(io=io, world=world).run()
        # The banner format from _on_shift_change uppercases SHIFT_NAMES[i]
        # — so "Forenoon" → "FORENOON" — and includes the day number.
        assert "── FORENOON " in io.transcript, (
            f"expected a Forenoon shift banner in the transcript after sleep; "
            f"shift is now {world.shift}; transcript tail:\n{io.transcript[-1500:]}"
        )
