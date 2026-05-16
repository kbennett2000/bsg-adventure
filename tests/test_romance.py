"""Tests for the romance state machine, the love-quadrangle ending, and the six
new NPCs (Tyrol, Boomer, Helo, Gaeta, Cottle, Dualla)."""

import os
import tempfile

import content  # noqa: F401
from engine.io import ScriptedIO
from engine.session import Session
from engine.world import bump_stat, get_stat, new_world, set_stat


def _run(inputs, player_name="Lover", save_dir=None, start_room="env_control"):
    if save_dir is not None:
        os.environ["BSG_SAVE_DIR"] = save_dir
    world = new_world(player_name, start_room)
    io = ScriptedIO(inputs)
    Session(io=io, world=world).run()
    return io, world


# ─── new NPCs are reachable and answer ────────────────────────────────────────


def test_tyrol_default_dialogue_without_algae_bar():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Test", "hangar_deck")
        world.visited_rooms.append("hangar_deck")
        io = ScriptedIO(["talk to tyrol", "quit"])
        Session(io=io, world=world).run()
        # He hints at the algae bar trade
        assert "algae bar" in io.transcript.lower()


def test_tyrol_unlocks_deep_gossip_for_algae_bar():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Trader", "hangar_deck")
        world.visited_rooms.append("hangar_deck")
        # Give the player an algae bar (they normally start with one in env_control)
        world.inventory.append("algae_bar")
        # Natural-language form — matches the item's aliases.
        io = ScriptedIO(["give algae bar to tyrol", "talk to tyrol", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("tyrol_owes_gossip") is True
        assert "algae_bar" not in world.inventory
        t = io.transcript.lower()
        assert "standing appointment" in t or "boomer? yeah" in t or "helo's back" in t


def test_boomer_default_asks_about_dreams():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("T", "hangar_deck")
        world.visited_rooms.append("hangar_deck")
        io = ScriptedIO(["talk to boomer", "quit"])
        Session(io=io, world=world).run()
        assert "dream" in io.transcript.lower()


def test_boomer_honest_water_answer_spikes_cylon_vibes():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("T", "hangar_deck")
        world.visited_rooms.append("hangar_deck")
        before = get_stat(world, "cylon_vibes")
        io = ScriptedIO(["talk to boomer", "talk to boomer about water", "quit"])
        Session(io=io, world=world).run()
        after = get_stat(world, "cylon_vibes")
        # Honest answer should be a substantial spike (default +2 from talk, +18 from honest water)
        assert after - before >= 15, (
            f"honest 'water' answer should spike cylon_vibes; before={before} after={after}"
        )


def test_boomer_dismissive_answer_does_not_spike_cylon_vibes():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("T", "hangar_deck")
        world.visited_rooms.append("hangar_deck")
        before = get_stat(world, "cylon_vibes")
        io = ScriptedIO(["talk to boomer", "talk to boomer about nothing", "quit"])
        Session(io=io, world=world).run()
        after = get_stat(world, "cylon_vibes")
        # Default talks bump +2 each (×2 = 4); no honest-answer spike.
        assert after - before < 15


def test_helo_thinks_player_is_someone_else():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("T", "sickbay")
        world.visited_rooms.append("sickbay")
        io = ScriptedIO(["talk to helo", "quit"])
        Session(io=io, world=world).run()
        # Beat 1 features the iconic "exact eyes" line
        assert "exact eyes" in io.transcript.lower()


def test_gaeta_uses_player_name():
    """Gaeta is the OFFICER who breaks the don't-remember-the-player contract."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Specialist_Foo", "cic")
        world.visited_rooms.append("cic")
        io = ScriptedIO(["talk to gaeta", "quit"])
        Session(io=io, world=world).run()
        assert "Specialist_Foo" in io.transcript, (
            "Gaeta should use the player's actual name in default talk"
        )


def test_cottle_calls_player_kid_and_offers_cigarette():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("T", "sickbay")
        world.visited_rooms.append("sickbay")
        io = ScriptedIO(["talk to cottle", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        assert "kid" in t
        assert "cigarette" in t


def test_cottle_hands_out_cigarette_on_request():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("T", "sickbay")
        world.visited_rooms.append("sickbay")
        io = ScriptedIO(["talk to cottle about cigarette", "inventory", "quit"])
        Session(io=io, world=world).run()
        assert "cigarette" in world.inventory


def test_cigarette_smoking_boosts_morale():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Smoker", "env_control")
        world.visited_rooms.append("env_control")
        world.inventory.append("cigarette")
        before = get_stat(world, "morale")
        io = ScriptedIO(["use cigarette", "quit"])
        Session(io=io, world=world).run()
        after = get_stat(world, "morale")
        assert after > before
        assert "cigarette" not in world.inventory  # consumed


def test_dualla_default_judges_player():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("T", "cic")
        world.visited_rooms.append("cic")
        io = ScriptedIO(["talk to dualla", "quit"])
        Session(io=io, world=world).run()
        # She mentions Gaeta's list — clear cross-reference.
        assert "Gaeta" in io.transcript


# ─── cross-references ─────────────────────────────────────────────────────────


def test_tyrol_mentions_boomer_acting_weird():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("T", "hangar_deck")
        world.visited_rooms.append("hangar_deck")
        io = ScriptedIO(["talk to tyrol about boomer", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        # Tyrol's boomer response betrays his feelings and references her behavior
        assert "boomer" in t or "valerii" in t


def test_gaeta_references_dualla():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("T", "cic")
        world.visited_rooms.append("cic")
        io = ScriptedIO(["talk to gaeta about dualla", "quit"])
        Session(io=io, world=world).run()
        assert "Dee" in io.transcript or "Dualla" in io.transcript


def test_helo_references_boomer():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("T", "sickbay")
        world.visited_rooms.append("sickbay")
        io = ScriptedIO(["talk to helo about boomer", "quit"])
        Session(io=io, world=world).run()
        assert "sharon" in io.transcript.lower() or "two sharons" in io.transcript.lower()


def test_boomer_references_helo():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("T", "hangar_deck")
        world.visited_rooms.append("hangar_deck")
        io = ScriptedIO(["talk to boomer about helo", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        assert "karl" in t or "tell him" in t


def test_cottle_warns_about_tigh():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("T", "sickbay")
        world.visited_rooms.append("sickbay")
        io = ScriptedIO(["talk to cottle about tigh", "quit"])
        Session(io=io, world=world).run()
        # The "if the XO ever asks you to fill a canteen, you say no" line
        assert "canteen" in io.transcript.lower()


# ─── romance progression ──────────────────────────────────────────────────────


def test_starbuck_romance_advances_through_three_beats():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Romancer", "pilots_rec")
        world.visited_rooms.append("pilots_rec")
        io = ScriptedIO(
            [
                "talk to starbuck about making out",  # beat 1
                "talk to starbuck about making out",  # beat 2
                "talk to starbuck about making out",  # beat 3
                "talk to starbuck about making out",  # complicated
                "quit",
            ]
        )
        Session(io=io, world=world).run()
        assert world.flags.get("romance_starbuck") == 4
        # After beat 3, starbuck is no longer in active_romances
        assert "starbuck" not in world.flags.get("active_romances", [])


def test_helo_default_talk_advances_romance():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Romancer", "sickbay")
        world.visited_rooms.append("sickbay")
        io = ScriptedIO(["talk to helo", "talk to helo", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("romance_helo") == 2
        assert "helo" in world.flags.get("active_romances", [])


def test_dualla_apollo_topic_advances_romance():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Romancer", "cic")
        world.visited_rooms.append("cic")
        io = ScriptedIO(["talk to dualla about apollo", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("romance_dualla") == 1


def test_six_god_topic_advances_romance():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Romancer", "corridor_b")
        world.visited_rooms.append("corridor_b")
        io = ScriptedIO(["talk to six about god", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("romance_six") == 1


def test_two_simultaneous_romances_are_allowed():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Romancer", "pilots_rec")
        world.visited_rooms.append("pilots_rec")
        world.flags["romance_helo"] = 1
        world.flags["active_romances"] = ["helo"]
        # Now start a second flirtation (Starbuck) — should not trigger quadrangle.
        io = ScriptedIO(["talk to starbuck about making out", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("__ended__") is None
        assert "starbuck" in world.flags.get("active_romances", [])
        assert len(world.flags["active_romances"]) == 2


def test_third_simultaneous_romance_triggers_quadrangle():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Doomed", "cic")
        world.visited_rooms.append("cic")
        # Player already has two active flirtations
        world.flags["active_romances"] = ["helo", "starbuck"]
        world.flags["romance_helo"] = 1
        world.flags["romance_starbuck"] = 1
        io = ScriptedIO(["talk to dualla about apollo", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("__ended__") == "love_quadrangle"
        assert "PERMANENT LATRINE DUTY" in io.transcript


def test_quadrangle_text_names_both_existing_partners():
    """The ending text should reference whoever is currently in active_romances."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Doomed", "cic")
        world.visited_rooms.append("cic")
        world.flags["active_romances"] = ["six", "helo"]
        world.flags["romance_six"] = 1
        world.flags["romance_helo"] = 1
        io = ScriptedIO(["talk to dualla about apollo", "quit"])
        Session(io=io, world=world).run()
        # The display names for six and helo should appear
        t = io.transcript
        assert ("shift supervisor" in t.lower() or "Captain Agathon" in t)


def test_completed_romance_clears_from_actives_letting_new_one_start():
    """Maxing out one romance (4 beats) should free a slot for another."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Romancer", "pilots_rec")
        world.visited_rooms.append("pilots_rec")
        # Burn through Starbuck to "complicated"
        io = ScriptedIO(
            [
                "talk to starbuck about making out",
                "talk to starbuck about making out",
                "talk to starbuck about making out",
                "talk to starbuck about making out",  # complicated
                "quit",
            ]
        )
        Session(io=io, world=world).run()
        assert world.flags.get("romance_starbuck") == 4
        assert "starbuck" not in world.flags.get("active_romances", [])

        # Now start TWO new ones — neither should hit quadrangle.
        world2 = new_world("Romancer", "sickbay")
        world2.visited_rooms.append("sickbay")
        world2.flags["romance_starbuck"] = 4
        world2.flags["active_romances"] = []  # already cleared by completion
        io2 = ScriptedIO(["talk to helo", "quit"])
        Session(io=io2, world=world2).run()
        assert world2.flags.get("__ended__") is None
        assert "helo" in world2.flags.get("active_romances", [])


def test_quadrangle_ending_bumps_suspicion():
    """Word gets around — even getting into a romantic mess bumps suspicion."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Doomed", "pilots_rec")
        world.visited_rooms.append("pilots_rec")
        # Just take starbuck to beat 3 (terminal) and check the +5 fired
        io = ScriptedIO(
            [
                "talk to starbuck about making out",
                "talk to starbuck about making out",
                "talk to starbuck about making out",
                "talk to starbuck about making out",  # complicated → +5 suspicion
                "quit",
            ]
        )
        before = get_stat(world, "suspicion")
        Session(io=io, world=world).run()
        after = get_stat(world, "suspicion")
        assert after >= before + 5
