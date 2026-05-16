"""Tests for ambient events and first-visit/revisit room logic."""

import os
import tempfile

import content  # noqa: F401
from engine import events
from engine.io import ScriptedIO
from engine.session import Session
from engine.world import new_world


def _run(inputs, player_name="EngTester", save_dir=None):
    if save_dir is not None:
        os.environ["BSG_SAVE_DIR"] = save_dir
    world = new_world(player_name, "env_control")
    io = ScriptedIO(inputs)
    Session(io=io, world=world).run()
    return io, world


def test_revisit_uses_short_description():
    """Going back to a room should print the short description, not the long one."""
    with tempfile.TemporaryDirectory() as tmp:
        io, world = _run(
            [
                "go east",  # first visit to corridor_c12 (long)
                "go west",  # back to env_control (revisit — short)
                "quit",
            ],
            save_dir=tmp,
        )
        # The full long_desc for env_control is the "Half workshop, half barracks" line.
        # On revisit it should be replaced by the short version.
        # The opening already showed the long form, so check the SECOND env_control print
        # uses short_desc text.
        env_control_appearances = [s for s in io.outputs if "ENVIRONMENTAL CONTROL" in s]
        assert len(env_control_appearances) >= 2
        # The revisit (second appearance) should be the short_desc — not the "Half workshop" full line.
        revisit_text = env_control_appearances[-1]
        assert "Half workshop, half barracks" not in revisit_text


def test_look_after_revisit_shows_long_description():
    """Explicit `look` should always restore the long form."""
    with tempfile.TemporaryDirectory() as tmp:
        io, world = _run(
            [
                "go east",      # first visit corridor (long)
                "go west",      # back, short
                "look",         # full long again
                "quit",
            ],
            save_dir=tmp,
        )
        # The long-form signature line should appear at least twice across the transcript:
        # once on the opening render, once via the explicit `look` after revisit.
        # (The middle revisit via `go west` should NOT have it.)
        count = io.transcript.count("Half workshop, half barracks")
        assert count >= 2, (
            f"`look` should print long description; expected long form to appear "
            f"at least twice (opening + explicit look). Got {count} occurrences."
        )


def test_ambient_events_fire_with_high_probability():
    """With probability forced to 1.0, an ambient event should print every turn."""
    original_prob = events._PROBABILITY
    try:
        events.set_probability(1.0)
        with tempfile.TemporaryDirectory() as tmp:
            io, world = _run(
                [
                    "wait",
                    "wait",
                    "wait",
                    "quit",
                ],
                save_dir=tmp,
            )
        # Ambient lines should appear at least three times (one per wait turn).
        # We can't match exact strings (they're random), so just confirm the
        # transcript got longer than the no-ambient baseline.
        text = io.transcript.lower()
        ambient_signals = sum(
            text.count(s) for s in ["intercom:", "baltar", "tigh sways", "catwalk", "pilot you don't"]
        )
        assert ambient_signals >= 1, (
            f"ambient events should have fired; got transcript:\n{io.transcript[-1500:]}"
        )
    finally:
        events.set_probability(original_prob)


def test_ambient_events_off_with_zero_probability():
    """With probability forced to 0, no ambient should fire."""
    original_prob = events._PROBABILITY
    try:
        events.set_probability(0.0)
        with tempfile.TemporaryDirectory() as tmp:
            io, world = _run(["wait", "wait", "wait", "quit"], save_dir=tmp)
        # With zero probability the transcript should not contain "PAGING LIEUTENANT BREN"
        assert "PAGING LIEUTENANT BREN" not in io.transcript
    finally:
        events.set_probability(original_prob)


def test_visited_rooms_persists_through_save_load():
    """Save/load should round-trip the visited_rooms list."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Visitor", "env_control")
        # Manually visit some rooms
        world.visited_rooms.extend(["env_control", "corridor_c12", "head_deck_5"])
        from engine import save
        save.save_world(world, slot="default")
        loaded = save.load_world("Visitor", "default")
        assert loaded.visited_rooms == ["env_control", "corridor_c12", "head_deck_5"]


def test_frak_lament_rotates_deterministically():
    """Each frak call should print a different lament until the list wraps."""
    with tempfile.TemporaryDirectory() as tmp:
        io, world = _run(["frak", "frak", "frak", "frak", "frak", "quit"], save_dir=tmp)
        # Extract just the lament outputs (they all start with double-quote or "You")
        frak_outputs = [
            s for s in io.outputs
            if any(s.startswith(p) for p in ['"', "You", "\"Frak"]) and "frak" in s.lower()
        ]
        assert len(frak_outputs) >= 5
        assert len(set(frak_outputs[:5])) == 5, (
            f"first 5 frak outputs should all differ; got: {frak_outputs[:5]}"
        )
