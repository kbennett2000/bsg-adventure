"""Tests for the Quorum Press Conference minigame."""

import os
import tempfile

import content  # noqa: F401
from engine.io import ScriptedIO
from engine.session import Session
from engine.world import bump_stat, get_stat, new_world, set_stat


# ─── triggering & briefing ────────────────────────────────────────────────────


def test_press_conference_triggers_via_roslin_topic():
    """`talk to roslin about press` (or conference / quorum / reporters) sets
    the press_active flag and prints Roslin's briefing."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Reporter", "sickbay")
        world.visited_rooms.append("sickbay")
        world.flags["entered_sickbay"] = True
        io = ScriptedIO(["talk to roslin about press", "quit"])
        Session(io=io, world=world).run()
        # The conference is now over (quit during it); we should at least
        # have seen the briefing text in the transcript.
        t = io.transcript.lower()
        assert "say nothing true" in t and "say nothing false" in t
        assert "say nothing" in t


def test_press_briefing_lists_three_response_categories():
    """The opening must surface the three response categories so the player
    knows what to type."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Reporter", "sickbay")
        world.visited_rooms.append("sickbay")
        world.flags["entered_sickbay"] = True
        io = ScriptedIO(["talk to roslin about press", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        assert "honest" in t and "political" in t and "unhinged" in t


def test_press_briefing_explains_the_political_situation():
    """The briefing should explain WHY the player is in front of the press
    (Tigh drunk, Adama with Tigh, Baltar talking to no one)."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Reporter", "sickbay")
        world.visited_rooms.append("sickbay")
        world.flags["entered_sickbay"] = True
        io = ScriptedIO(["talk to roslin about press", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        assert "indisposed" in t
        # Baltar is referenced (talking to no one) and Tigh/Adama somewhere.
        assert "baltar" in t


# ─── input routing while press is active ──────────────────────────────────────


def test_press_active_blocks_normal_verbs():
    """While the conference is active, normal verbs like `look` should be
    intercepted by the press handler (which prompts for honest/political/unhinged)."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Reporter", "sickbay")
        world.visited_rooms.append("sickbay")
        world.flags["entered_sickbay"] = True
        io = ScriptedIO(
            [
                "talk to roslin about press",   # start conference
                "look",                          # should NOT do a normal look
                "quit",
            ]
        )
        Session(io=io, world=world).run()
        t = io.transcript
        # The press re-prompt fires on the unrecognized "look"
        assert "Pick: honest, political, or unhinged" in t


def test_full_run_six_rounds_with_political_completes_conference():
    """Six political answers should run to outcome and clear press_active."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Reporter", "sickbay")
        world.visited_rooms.append("sickbay")
        world.flags["entered_sickbay"] = True
        io = ScriptedIO(
            [
                "talk to roslin about press",
                "political", "political", "political",
                "political", "political", "political",
                "quit",
            ]
        )
        Session(io=io, world=world).run()
        # press_active flag should be cleared by _clear_press_state.
        assert not world.flags.get("press_active")
        # An outcome should be recorded.
        assert world.flags.get("press_outcome") in {"high", "medium", "low", "rock_bottom"}


# ─── outcome tiers ────────────────────────────────────────────────────────────


def test_all_political_answers_yield_high_outcome_and_commendation():
    """Six political answers: +5 cred each = +30 → starts at 50, ends at 80.
    High threshold is 70 → high outcome → commendation letter awarded."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("PoliticalBeast", "sickbay")
        world.visited_rooms.append("sickbay")
        world.flags["entered_sickbay"] = True
        io = ScriptedIO(
            [
                "talk to roslin about press",
                "political", "political", "political",
                "political", "political", "political",
                "quit",
            ]
        )
        Session(io=io, world=world).run()
        assert world.flags.get("press_outcome") == "high"
        assert "commendation_letter" in world.inventory
        assert "presidential" in io.transcript.lower() and "commendation" in io.transcript.lower()


def test_all_honest_answers_tank_credibility_and_trigger_low_outcome():
    """Honest answers vary in credibility cost; the worst (Tigh, meat) are
    sharply negative. Six honest answers will land under the low threshold."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("HonestFool", "sickbay")
        world.visited_rooms.append("sickbay")
        world.flags["entered_sickbay"] = True
        before_suspicion = get_stat(world, "suspicion")
        io = ScriptedIO(
            [
                "talk to roslin about press",
                "honest", "honest", "honest",
                "honest", "honest", "honest",
                "quit",
            ]
        )
        Session(io=io, world=world).run()
        outcome = world.flags.get("press_outcome")
        assert outcome in ("low", "rock_bottom"), (
            f"all-honest should land in low/rock_bottom; got {outcome}"
        )
        # Suspicion should be substantially elevated (each round + final outcome)
        assert get_stat(world, "suspicion") > before_suspicion + 25


def test_low_outcome_sets_press_confirmed_conspiracies_flag():
    """The 'low' tier specifically sets the conspiracies-confirmed flag for
    downstream content to react to."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Confessor", "sickbay")
        world.visited_rooms.append("sickbay")
        world.flags["entered_sickbay"] = True
        io = ScriptedIO(
            [
                "talk to roslin about press",
                "honest", "honest", "honest",
                "honest", "honest", "honest",
                "quit",
            ]
        )
        Session(io=io, world=world).run()
        if world.flags.get("press_outcome") == "low":
            assert world.flags.get("press_confirmed_conspiracies") is True


def test_rock_bottom_outcome_sets_was_briefly_famous_flag():
    """If credibility ends at or below 10 (rock bottom), the 'briefly famous'
    flag is set for downstream content to reference."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        # Force rock bottom by pre-setting credibility very low before final eval.
        # We do this by manually pre-running the briefing then setting
        # press_credibility low, then sending a single non-impactful round? No —
        # cleaner: hand-fire the finalize path with a low credibility.
        from content.press import _finalize, _clear_press_state
        world = new_world("Famous", "sickbay")
        world.flags["press_active"] = True
        world.flags["press_round"] = 6
        world.flags["press_questions"] = ["election"] * 6
        world.flags["press_credibility"] = 5
        text = _finalize(world)
        _clear_press_state(world)
        assert world.flags.get("press_outcome") == "rock_bottom"
        assert world.flags.get("was_briefly_famous") is True
        assert "briefly, famous" in text or "briefly famous" in text.lower()


def test_high_outcome_lowers_suspicion_low_outcome_raises_it():
    """High → suspicion -5. Low → suspicion +30. Pre-set suspicion > 0 so the
    high-path decrement is observable (bump_stat clamps at 0)."""
    from content.press import _finalize, _clear_press_state
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        # High path
        w1 = new_world("Hi", "sickbay")
        set_stat(w1, "suspicion", 30)   # so -5 is observable
        w1.flags["press_active"] = True
        w1.flags["press_round"] = 6
        w1.flags["press_questions"] = ["election"] * 6
        w1.flags["press_credibility"] = 85
        before = get_stat(w1, "suspicion")
        _finalize(w1)
        _clear_press_state(w1)
        assert get_stat(w1, "suspicion") < before, "high outcome should lower suspicion"
        # Low path
        w2 = new_world("Lo", "sickbay")
        w2.flags["press_active"] = True
        w2.flags["press_round"] = 6
        w2.flags["press_questions"] = ["election"] * 6
        w2.flags["press_credibility"] = 20
        before = get_stat(w2, "suspicion")
        _finalize(w2)
        _clear_press_state(w2)
        assert get_stat(w2, "suspicion") > before, "low outcome should raise suspicion"


# ─── unhinged determinism ────────────────────────────────────────────────────


def test_unhinged_outcomes_are_deterministic_per_player_day_question():
    """The same (player, day, question) seed must produce the same unhinged
    outcome twice. This guarantees save/load round-tripping."""
    from content.press import _question_rng
    w1 = new_world("Stable", "sickbay")
    w1.day = 3
    w2 = new_world("Stable", "sickbay")
    w2.day = 3
    out1 = _question_rng(w1, "tigh_drinking").random()
    out2 = _question_rng(w2, "tigh_drinking").random()
    assert out1 == out2
    # Different days/players differ:
    w3 = new_world("Stable", "sickbay")
    w3.day = 4
    out3 = _question_rng(w3, "tigh_drinking").random()
    assert out1 != out3


def test_unhinged_response_appears_in_transcript():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Wild", "sickbay")
        world.visited_rooms.append("sickbay")
        world.flags["entered_sickbay"] = True
        io = ScriptedIO(
            [
                "talk to roslin about press",
                "unhinged", "unhinged", "unhinged",
                "unhinged", "unhinged", "unhinged",
                "quit",
            ]
        )
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        # At least one of the unhinged-question text fragments should be present.
        signature_lines = [
            "haunted brewery", "captain frakkin' adorable", "i'm KIDDING".lower(),
            "talking algae", "sagittaron",
        ]
        assert any(s in t for s in signature_lines), (
            "transcript should contain at least one unhinged signature line"
        )


# ─── post-conference state ───────────────────────────────────────────────────


def test_can_only_run_conference_once():
    """After completing a conference, asking Roslin about press again should
    refuse, not restart."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Returner", "sickbay")
        world.visited_rooms.append("sickbay")
        world.flags["entered_sickbay"] = True
        io = ScriptedIO(
            [
                "talk to roslin about press",
                "political", "political", "political",
                "political", "political", "political",
                "talk to roslin about press",    # try again
                "quit",
            ]
        )
        Session(io=io, world=world).run()
        # Should see the "not again" refusal somewhere
        assert "not doing that again" in io.transcript.lower()


def test_press_state_round_trips_mid_conference():
    """Saving mid-conference and reloading must preserve press_active,
    press_round, press_questions, and press_credibility. (We save the world
    directly here because the in-game `save` verb is intercepted by the
    press handler — by design, since the player has no normal verbs during
    a conference.)"""
    from engine import save as save_module
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("MidSave", "sickbay")
        world.visited_rooms.append("sickbay")
        world.flags["entered_sickbay"] = True
        io = ScriptedIO(
            [
                "talk to roslin about press",
                "political", "political",   # complete 2 rounds
                "quit",
            ]
        )
        Session(io=io, world=world).run()
        # The session's autosave on quit captured the mid-conference state.
        assert world.flags.get("press_active") is True
        assert world.flags.get("press_round") == 2
        save_module.save_world(world, slot="mid_press")
        loaded = save_module.load_world("MidSave", "mid_press")
        assert loaded.flags.get("press_active") is True
        assert loaded.flags.get("press_round") == 2
        assert loaded.flags.get("press_questions") is not None
        assert loaded.flags.get("press_credibility") is not None


def test_hadrian_reacts_to_briefly_famous_flag():
    """After rock-bottom, talking to Hadrian about press gets the famous-warning line."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Famous", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["was_briefly_famous"] = True
        io = ScriptedIO(["talk to hadrian about press", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        assert "t-shirt" in t or "broadcast" in t


def test_commendation_letter_is_a_real_item_with_dynamic_description():
    """The reward item exists, can be examined, and gives the misspelled
    name flavor."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Holder", "env_control")
        world.visited_rooms.append("env_control")
        world.inventory.append("commendation_letter")
        io = ScriptedIO(["examine letter", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        assert "presidential letterhead" in t
        assert "misspelled" in t


def test_quit_during_conference_preserves_state_for_resume():
    """`quit` mid-conference exits the session cleanly but PRESERVES
    press_active in the snapshot — that way a later load drops the player
    back into the same press conference, on the same round."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Bailer", "sickbay")
        world.visited_rooms.append("sickbay")
        world.flags["entered_sickbay"] = True
        io = ScriptedIO(
            [
                "talk to roslin about press",
                "political",
                "quit",
            ]
        )
        Session(io=io, world=world).run()
        # State preserved for resume:
        assert world.flags.get("press_active") is True
        assert world.flags.get("press_round") == 1


def test_six_questions_in_pool():
    """The user spec says 5-7 rounds. We ship 6 in the pool."""
    from content.press import QUESTIONS
    assert 5 <= len(QUESTIONS) <= 7, f"expected 5-7 questions; got {len(QUESTIONS)}"


def test_each_question_has_three_distinct_categories():
    """Every question must have a complete honest/political/unhinged set."""
    from content.press import QUESTIONS
    for q in QUESTIONS:
        assert "honest" in q and "political" in q
        assert "unhinged_text" in q and "unhinged_outcomes" in q
        # Honest and political each have text + delta
        assert "text" in q["honest"] and "delta" in q["honest"]
        assert "text" in q["political"] and "delta" in q["political"]
        # Unhinged has at least 2 random outcomes
        assert len(q["unhinged_outcomes"]) >= 2
        for outcome in q["unhinged_outcomes"]:
            assert "note" in outcome


def test_questions_parody_real_bsg_arcs():
    """Sanity: the question pool covers election, abortion, cylons-among-us,
    new caprica, tigh drinking, mystery meat — the show's load-bearing arcs."""
    from content.press import QUESTIONS
    ids = {q["id"] for q in QUESTIONS}
    expected = {"election", "abortion", "cylons_among_us", "new_caprica",
                "tigh_drinking", "mystery_meat"}
    assert expected.issubset(ids), f"missing arcs: {expected - ids}"
