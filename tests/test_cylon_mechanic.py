"""Tests for the hidden Cylon resurrection mechanic.

The mechanic is invisible to non-Cylon playthroughs. These tests verify:
  - cylon_vibes ≥ 75 silently flips `is_cylon` (no UI surfacing)
  - The Cylon detector becomes deterministic for Cylons (always beeps at them)
  - Cottle's bloodwork remark fires once when the player is Cylon
  - Hadrian's pool contains the 'two decks at once' rumor
  - Cylon-variant examines reveal "things the player shouldn't know"
  - Cylon-only Watchtower ambient is registered (3x for higher frequency)
  - Death endings resurrect Cylons (spaced, forbidden_knowledge)
  - The 3rd resurrection triggers the Download Complete ending
  - Non-Cylon death endings still end the game as before
  - World drift: NPCs become suspicious / dead across resurrections
"""

import os
import tempfile

import content  # noqa: F401
from engine.io import ScriptedIO
from engine.session import Session
from engine.world import bump_stat, get_stat, new_world, set_stat


# ─── silent flag flip ─────────────────────────────────────────────────────────


def test_cylon_vibes_75_silently_sets_is_cylon():
    """When cylon_vibes reaches the threshold, the hidden flag flips. There
    is no announcement to the player."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Tester", "env_control")
        world.visited_rooms.append("env_control")
        set_stat(world, "cylon_vibes", 74)
        assert not world.flags.get("is_cylon")
        # Advance one turn with a small cylon_vibes bump to cross 75.
        # We do this by entering corridor_b (a Six encounter may fire — but
        # we'll just directly call bump_stat to keep this deterministic).
        bump_stat(world, "cylon_vibes", 5)
        io = ScriptedIO(["salute", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("is_cylon") is True


def test_is_cylon_never_appears_in_status_output():
    """The mechanic must be completely invisible. status/look/inventory must
    never tell the player they're a Cylon."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Tester", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["is_cylon"] = True   # pretend they crossed
        io = ScriptedIO(["status", "look", "inventory", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        forbidden = ["is_cylon", "you are a cylon", "you're a cylon", "you are cylon"]
        for marker in forbidden:
            assert marker not in t, f"status/look/inventory leaked '{marker}' to the player"


def test_threshold_only_flips_once():
    """Even if cylon_vibes oscillates, is_cylon stays True once set."""
    from engine.world import set_stat
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Tester", "env_control")
        world.visited_rooms.append("env_control")
        set_stat(world, "cylon_vibes", 80)
        io = ScriptedIO(["salute", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("is_cylon") is True
        # Drop cylon_vibes — flag stays.
        set_stat(world, "cylon_vibes", 10)
        assert world.flags.get("is_cylon") is True


# ─── Cylon detector: deterministic for Cylons ────────────────────────────────


def test_cylon_detector_always_beeps_at_cylon_player():
    """Run 10 detector uses for a Cylon. Every one should beep at them."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("CylonPlayer", "baltars_lab")
        world.visited_rooms.append("baltars_lab")
        world.flags["entered_baltars_lab"] = True
        world.flags["is_cylon"] = True
        world.inventory.append("cylon_detector")
        # Use the detector 10 times.
        cmds = []
        for _ in range(10):
            cmds.append("use detector")
        cmds.append("quit")
        io = ScriptedIO(cmds)
        Session(io=io, world=world).run()
        # Every detector-use response should be the "at you" variant.
        beep_at_you = io.transcript.count("It points at you")
        assert beep_at_you >= 10, (
            f"Cylon detector should always beep at the player; "
            f"got {beep_at_you} 'points at you' responses across 10 uses"
        )


def test_cylon_detector_random_for_non_cylon():
    """For a non-Cylon, the detector keeps its random behavior."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("NormalPlayer", "baltars_lab")
        world.visited_rooms.append("baltars_lab")
        world.flags["entered_baltars_lab"] = True
        world.inventory.append("cylon_detector")
        cmds = ["use detector"] * 30 + ["quit"]
        io = ScriptedIO(cmds)
        Session(io=io, world=world).run()
        # Across 30 random rolls, the detector should NOT have always pointed
        # at the player. At least some should be NPC beeps.
        npc_beeps = io.transcript.count("very deliberately, at")
        assert npc_beeps >= 1, (
            f"non-Cylon detector should occasionally point at NPCs; got {npc_beeps}"
        )


# ─── Cottle reaction ──────────────────────────────────────────────────────────


def test_cottle_bloodwork_remark_when_is_cylon():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("CylonPatient", "sickbay")
        world.visited_rooms.append("sickbay")
        world.flags["entered_sickbay"] = True
        world.flags["is_cylon"] = True
        io = ScriptedIO(["talk to cottle", "quit"])
        Session(io=io, world=world).run()
        assert "bloodwork is" in io.transcript.lower()
        assert "huh" in io.transcript.lower()


def test_cottle_does_not_remark_for_non_cylon():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Normal", "sickbay")
        world.visited_rooms.append("sickbay")
        world.flags["entered_sickbay"] = True
        io = ScriptedIO(["talk to cottle", "quit"])
        Session(io=io, world=world).run()
        assert "bloodwork is" not in io.transcript.lower()


# ─── Hadrian 'two decks at once' rumor + suspicious-Hadrian dialogue ─────────


def test_hadrian_two_decks_rumor_in_pool():
    """The discoverability hint is present in Hadrian's rumor pool."""
    from content.npcs import HADRIAN_RUMORS
    joined = " ".join(HADRIAN_RUMORS).lower()
    assert "two decks" in joined or "two decks at once" in joined


def test_hadrian_suspicious_after_first_resurrection_flag():
    """If npc_suspicious_hadrian is set, his first default talk gets a
    paranoid prefix asking if the player's been 'around.'"""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Resurrected", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["npc_suspicious_hadrian"] = True
        io = ScriptedIO(["talk to hadrian", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        assert "been around" in t or "whole time" in t or "on deck five" in t.lower()


# ─── examines reveal "things the player shouldn't know" ──────────────────────


def test_pipes_examine_reveals_specs_when_cylon():
    """Cylon variant of env_control 'examine pipes' mentions valve specs the
    player shouldn't know."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("CylonOnDuty", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["is_cylon"] = True
        io = ScriptedIO(["examine pipes", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        # The Cylon variant mentions "spec" / "factory" / "how you know"
        assert "spec" in t or "factory" in t or "don't know how" in t


def test_pipes_examine_is_normal_for_non_cylon():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Normal", "env_control")
        world.visited_rooms.append("env_control")
        io = ScriptedIO(["examine pipes", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        # Non-cylon line: "Coolant pipes. They hum. ..."
        assert "they hum" in t


def test_viper_examine_reveals_internals_when_cylon():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("CylonViper", "hangar_deck")
        world.visited_rooms.append("hangar_deck")
        world.flags["is_cylon"] = True
        io = ScriptedIO(["examine viper", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        assert ("autoloader" in t or "canopy seal" in t or
                "never been in a viper" in t)


def test_model_ship_examine_reveals_history_when_cylon():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("CylonInQuarters", "adamas_quarters")
        world.visited_rooms.append("adamas_quarters")
        world.flags["entered_adamas_quarters"] = True
        world.flags["is_cylon"] = True
        io = ScriptedIO(["examine model", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        assert "picon" in t and "never been to picon" in t


# ─── Cylon-only Watchtower ambient is registered ─────────────────────────────


def test_cylon_watchtower_ambient_registered():
    """A Cylon-only ambient callable should be in the events registry (the
    `_watchtower_cylon_only` callable). Registered 3x for higher frequency."""
    from engine import events
    from content.flavor import _watchtower_cylon_only
    count = sum(1 for entry in events._REGISTERED if entry is _watchtower_cylon_only)
    assert count >= 3, (
        f"Cylon Watchtower ambient should be registered ≥3 times for higher "
        f"frequency; got {count}"
    )


def test_cylon_watchtower_ambient_returns_none_for_non_cylon():
    from content.flavor import _watchtower_cylon_only
    world = new_world("Normal", "env_control")
    assert _watchtower_cylon_only(world) is None


def test_cylon_watchtower_ambient_returns_text_for_cylon():
    from content.flavor import _watchtower_cylon_only
    world = new_world("Cylon", "env_control")
    world.flags["is_cylon"] = True
    out = _watchtower_cylon_only(world)
    assert out is not None
    assert "watchtower" in out.lower()


# ─── resurrection on death endings ───────────────────────────────────────────


def test_spaced_ending_resurrects_a_cylon():
    """When a Cylon hits the spaced ending, they wake in a resurrection tank
    instead of game-over."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("UndeadOne", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["is_cylon"] = True
        # Force the spaced ending via global suspicion = 100.
        set_stat(world, "suspicion", 100)
        io = ScriptedIO(["salute", "quit"])
        Session(io=io, world=world).run()
        # __ended__ should have been CLEARED (not game-over); resurrection_count = 1
        assert world.flags.get("__ended__") is None, (
            "death ending should have been cleared by resurrection"
        )
        assert world.flags.get("resurrection_count") == 1
        # Player should be in env_control (resurrection tank → bunk)
        assert world.current_room == "env_control"
        # The screen-goes-white narrative should appear
        assert "wake up" in io.transcript.lower()


def test_forbidden_knowledge_ending_resurrects_a_cylon():
    """Reading the envelope as a Cylon → resurrection, not game-over."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("UndeadReader", "cic")
        world.visited_rooms.append("cic")
        world.flags["entered_cic"] = True
        world.flags["is_cylon"] = True
        world.inventory.append("sealed_envelope")
        io = ScriptedIO(["use envelope", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("__ended__") is None
        assert world.flags.get("resurrection_count") == 1


def test_resurrection_advances_day_and_resets_exhaustion():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Tank", "head_deck_5")
        world.visited_rooms.append("head_deck_5")
        world.flags["is_cylon"] = True
        world.flags["entered_head"] = True
        world.day = 3
        set_stat(world, "exhaustion", 80)
        set_stat(world, "suspicion", 100)   # force spaced
        io = ScriptedIO(["salute", "quit"])
        Session(io=io, world=world).run()
        assert world.day == 4
        assert world.shift == 0
        assert get_stat(world, "exhaustion") <= 1


def test_first_resurrection_makes_hadrian_suspicious():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("R1", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["is_cylon"] = True
        set_stat(world, "suspicion", 100)
        io = ScriptedIO(["salute", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("npc_suspicious_hadrian") is True


def test_second_resurrection_kills_helo():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("R2", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["is_cylon"] = True
        world.flags["resurrection_count"] = 1
        set_stat(world, "suspicion", 100)
        io = ScriptedIO(["salute", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("npc_dead_helo") is True


def test_dead_npc_is_not_in_room_present_list():
    """If npc_dead_helo is set, Helo doesn't appear in sickbay's Present line."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Mourner", "sickbay")
        world.visited_rooms.append("sickbay")
        world.flags["entered_sickbay"] = True
        world.flags["npc_dead_helo"] = True
        io = ScriptedIO(["look", "quit"])
        Session(io=io, world=world).run()
        present_lines = []
        for out in io.outputs:
            for line in out.split("\n"):
                if line.startswith("Present:"):
                    present_lines.append(line)
        assert present_lines
        assert all("Captain Agathon" not in ln for ln in present_lines)


# ─── 3rd resurrection → Download Complete ────────────────────────────────────


def test_third_resurrection_triggers_download_complete():
    """The 3rd resurrection replaces the normal wake-up with the final
    Download Complete ending."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("R3", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["is_cylon"] = True
        world.flags["resurrection_count"] = 2
        set_stat(world, "suspicion", 100)
        io = ScriptedIO(["salute", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("__ended__") == "download_complete"
        assert "DOWNLOAD COMPLETE" in io.transcript
        # And the existential dread + latrine duty signature lines:
        t = io.transcript.lower()
        assert "latrine" in t
        assert "download" in t


# ─── non-Cylon path is unchanged ─────────────────────────────────────────────


def test_non_cylon_spaced_ending_still_ends_the_game():
    """The mechanic must be invisible to non-Cylons. Spaced still ends."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("MortalPlayer", "env_control")
        world.visited_rooms.append("env_control")
        # is_cylon NOT set
        set_stat(world, "suspicion", 100)
        io = ScriptedIO(["salute", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("__ended__") == "spaced"
        assert world.flags.get("resurrection_count", 0) == 0


def test_non_cylon_hero_ending_unaffected():
    """Hero is a win, not a death — resurrection should NEVER trigger here
    even if the player happens to be Cylon."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("CylonHero", "cic")
        world.visited_rooms.append("cic")
        world.flags["entered_cic"] = True
        world.flags["realized_napkin_is_coords"] = True
        world.flags["is_cylon"] = True       # even as a Cylon...
        world.inventory.append("napkin")
        io = ScriptedIO(["give napkin to adama", "quit"])
        Session(io=io, world=world).run()
        # Hero, not download_complete, not cleared.
        assert world.flags.get("__ended__") == "hero"
        assert world.flags.get("resurrection_count", 0) == 0


# ─── state round-trips through save/load ─────────────────────────────────────


def test_cylon_state_round_trips():
    """is_cylon, resurrection_count, and the NPC flags must round-trip."""
    from engine import save as save_module
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Saver", "env_control")
        world.flags["is_cylon"] = True
        world.flags["resurrection_count"] = 2
        world.flags["npc_suspicious_hadrian"] = True
        world.flags["npc_dead_helo"] = True
        save_module.save_world(world, slot="default")
        loaded = save_module.load_world("Saver", "default")
        assert loaded.flags["is_cylon"] is True
        assert loaded.flags["resurrection_count"] == 2
        assert loaded.flags["npc_suspicious_hadrian"] is True
        assert loaded.flags["npc_dead_helo"] is True
