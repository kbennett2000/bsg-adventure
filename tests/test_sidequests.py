"""Tests for the five side quests, three hidden rooms, and forbidden-knowledge ending."""

import os
import tempfile

import content  # noqa: F401
from engine.io import ScriptedIO
from engine.session import Session
from engine.world import bump_stat, get_stat, new_world, set_stat


def _run(inputs, player_name="QuestTester", save_dir=None, start_room="env_control"):
    if save_dir is not None:
        os.environ["BSG_SAVE_DIR"] = save_dir
    world = new_world(player_name, start_room)
    io = ScriptedIO(inputs)
    Session(io=io, world=world).run()
    return io, world


# ─── Quest 1: Tigh's Secret Stash ─────────────────────────────────────────────


def test_stash_flask_under_loose_tile():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Sneak", "head_deck_5")
        world.visited_rooms.append("head_deck_5")
        io = ScriptedIO(["examine loose tile", "take flask", "quit"])
        Session(io=io, world=world).run()
        assert "flask" in world.inventory
        assert world.flags.get("found_flask") is True
        # Suspicion should have bumped from sneaking
        assert get_stat(world, "suspicion") >= 5


def test_stash_thermos_in_mess_kitchen():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Sneak", "mess_hall")
        world.visited_rooms.append("mess_hall")
        io = ScriptedIO(["examine kitchen", "take thermos", "quit"])
        Session(io=io, world=world).run()
        assert "stash_bottle_mess" in world.inventory


def test_stash_grease_can_in_raptor():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Sneak", "hangar_deck")
        world.visited_rooms.append("hangar_deck")
        io = ScriptedIO(["examine raptor", "take grease can", "quit"])
        Session(io=io, world=world).run()
        assert "stash_bottle_hangar" in world.inventory


def test_drinking_any_stash_bottle_gives_swig_reward():
    """The swig: +morale, +exhaustion, +small suspicion."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Drinker", "env_control")
        world.visited_rooms.append("env_control")
        world.inventory.append("flask")
        before_m = get_stat(world, "morale")
        before_e = get_stat(world, "exhaustion")
        io = ScriptedIO(["drink flask", "quit"])
        Session(io=io, world=world).run()
        after_m = get_stat(world, "morale")
        after_e = get_stat(world, "exhaustion")
        assert after_m > before_m
        assert after_e > before_e


def test_returning_all_three_bottles_completes_stash_quest():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Returner", "head_deck_5")
        world.visited_rooms.append("head_deck_5")
        # Skip the witnessing-Tigh suspicion bump for this isolated test.
        world.flags["entered_head"] = True
        world.inventory.extend(["flask", "stash_bottle_mess", "stash_bottle_hangar"])
        io = ScriptedIO(
            [
                "give flask to tigh",
                "give thermos to tigh",
                "give grease can to tigh",
                "quit",
            ]
        )
        Session(io=io, world=world).run()
        assert world.flags.get("quest_stash_complete") is True
        assert "frak ME" in io.transcript  # signature acknowledgment


# ─── Quest 2: The Missing Wrench ──────────────────────────────────────────────


def test_wrench_pickup_blocked_without_baltar_misdirection():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Thief", "baltars_lab")
        world.visited_rooms.append("baltars_lab")
        io = ScriptedIO(["take wrench", "quit"])
        Session(io=io, world=world).run()
        assert "wrench" not in world.inventory
        assert "put that down" in io.transcript.lower() or "WHAT" in io.transcript


def test_wrench_pickup_succeeds_after_juno_misdirection():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Misdirecter", "baltars_lab")
        world.visited_rooms.append("baltars_lab")
        io = ScriptedIO(
            [
                "talk to baltar about juno",   # sets baltar_distracted
                "take wrench",
                "inventory",
                "quit",
            ]
        )
        Session(io=io, world=world).run()
        assert world.flags.get("baltar_distracted") is True
        assert "wrench" in world.inventory


def test_returning_wrench_to_tyrol_completes_quest():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Returner", "hangar_deck")
        world.visited_rooms.append("hangar_deck")
        world.inventory.append("wrench")
        before_m = get_stat(world, "morale")
        io = ScriptedIO(["give wrench to tyrol", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("quest_wrench_complete") is True
        assert "wrench" not in world.inventory
        assert get_stat(world, "morale") > before_m


def test_tyrol_wrench_topic_changes_after_completion():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Friend", "hangar_deck")
        world.visited_rooms.append("hangar_deck")
        world.flags["quest_wrench_complete"] = True
        io = ScriptedIO(["talk to tyrol about wrench", "quit"])
        Session(io=io, world=world).run()
        assert "owe you" in io.transcript.lower()


# ─── Quest 3: Cards Night (4 outcomes) ────────────────────────────────────────


def test_cards_quest_starts_with_choice_menu():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Player", "pilots_rec")
        world.visited_rooms.append("pilots_rec")
        io = ScriptedIO(["talk to starbuck about cards", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        assert "graceful" in t and "flirt" in t and "cheat" in t and "accuse" in t


def test_cards_graceful_outcome():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Player", "pilots_rec")
        world.visited_rooms.append("pilots_rec")
        before = get_stat(world, "morale")
        io = ScriptedIO(
            ["talk to starbuck about cards", "talk to starbuck about graceful", "quit"]
        )
        Session(io=io, world=world).run()
        assert world.flags.get("quest_cards_choice") == "graceful"
        assert get_stat(world, "morale") > before


def test_cards_flirt_outcome_bumps_romance():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Player", "pilots_rec")
        world.visited_rooms.append("pilots_rec")
        io = ScriptedIO(
            ["talk to starbuck about cards", "talk to starbuck about flirt", "quit"]
        )
        Session(io=io, world=world).run()
        assert world.flags.get("quest_cards_choice") == "flirt"
        assert world.flags.get("romance_starbuck", 0) >= 1


def test_cards_cheat_outcome_drains_morale_and_spikes_suspicion():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Cheater", "pilots_rec")
        world.visited_rooms.append("pilots_rec")
        before_m = get_stat(world, "morale")
        before_s = get_stat(world, "suspicion")
        io = ScriptedIO(
            ["talk to starbuck about cards", "talk to starbuck about cheat", "quit"]
        )
        Session(io=io, world=world).run()
        assert world.flags.get("quest_cards_choice") == "cheat"
        assert get_stat(world, "morale") < before_m
        assert get_stat(world, "suspicion") > before_s


def test_cards_accuse_outcome_terminates_starbuck_romance():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Bold", "pilots_rec")
        world.visited_rooms.append("pilots_rec")
        io = ScriptedIO(
            ["talk to starbuck about cards", "talk to starbuck about accuse", "quit"]
        )
        Session(io=io, world=world).run()
        assert world.flags.get("quest_cards_choice") == "accuse"
        assert world.flags.get("romance_starbuck") == 4


# ─── Quest 4: Mystery Meat ────────────────────────────────────────────────────


def test_cook_refuses_to_discuss_the_meat():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Curious", "mess_hall")
        world.visited_rooms.append("mess_hall")
        io = ScriptedIO(["talk to cook about meat", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        assert "not going to talk about" in t or "get out of my kitchen" in t


def test_algae_processor_solves_mystery_meat():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Solver", "env_control")
        world.visited_rooms.append("env_control")
        world.inventory.append("wrench")  # required to open hatch
        before_m = get_stat(world, "morale")
        io = ScriptedIO(["go down", "quit"])
        Session(io=io, world=world).run()
        assert world.current_room == "algae_processor"
        assert world.flags.get("mystery_meat_solved") is True
        # Learning the truth is upsetting → morale drop
        assert get_stat(world, "morale") < before_m


# ─── Quest 5: The Prophecy ────────────────────────────────────────────────────


def test_prophecy_quest_starts_with_white_robe_question():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Chosen", "sickbay")
        world.visited_rooms.append("sickbay")
        io = ScriptedIO(["talk to roslin about prophecy", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        assert "white robe" in t


def test_prophecy_yes_is_wrong_answer():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Honest", "sickbay")
        world.visited_rooms.append("sickbay")
        before_s = get_stat(world, "suspicion")
        io = ScriptedIO(
            ["talk to roslin about prophecy", "talk to roslin about yes", "quit"]
        )
        Session(io=io, world=world).run()
        assert world.flags.get("quest_prophecy_choice") == "yes"
        assert get_stat(world, "suspicion") > before_s


def test_prophecy_no_is_also_wrong_answer():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Deflector", "sickbay")
        world.visited_rooms.append("sickbay")
        before_m = get_stat(world, "morale")
        io = ScriptedIO(
            ["talk to roslin about prophecy", "talk to roslin about no", "quit"]
        )
        Session(io=io, world=world).run()
        assert world.flags.get("quest_prophecy_choice") == "no"
        assert get_stat(world, "morale") < before_m


# ─── Hidden rooms ─────────────────────────────────────────────────────────────


def test_algae_processor_accessible_only_with_wrench():
    """Without the wrench, the hatch isn't openable."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Stuck", "env_control")
        world.visited_rooms.append("env_control")
        io = ScriptedIO(["go down", "quit"])
        Session(io=io, world=world).run()
        assert world.current_room == "env_control"
        assert "no way down" in io.transcript.lower()


def test_algae_processor_stays_accessible_after_wrench_returned():
    """Once you've been through, the hatch stays unbolted."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Tour", "env_control")
        world.visited_rooms.append("env_control")
        world.flags["entered_algae_processor"] = True
        # No wrench in inventory
        io = ScriptedIO(["go down", "quit"])
        Session(io=io, world=world).run()
        assert world.current_room == "algae_processor"


def test_adamas_workshop_hidden_by_default():
    """Below the suspicion threshold, the panel reads as just a wall."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Oblivious", "adamas_quarters")
        world.visited_rooms.append("adamas_quarters")
        io = ScriptedIO(["examine panel", "go north", "quit"])
        Session(io=io, world=world).run()
        assert world.current_room == "adamas_quarters"
        assert "looks like a wall" in io.transcript.lower()


def test_adamas_workshop_visible_at_high_suspicion():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Paranoid", "adamas_quarters")
        world.visited_rooms.append("adamas_quarters")
        set_stat(world, "suspicion", 50)
        io = ScriptedIO(["examine panel", "go north", "quit"])
        Session(io=io, world=world).run()
        assert world.current_room == "adamas_workshop"
        assert world.flags.get("entered_adamas_workshop") is True


def test_storage_bay_hidden_at_low_cylon_vibes():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Normie", "hangar_deck")
        world.visited_rooms.append("hangar_deck")
        io = ScriptedIO(["examine deck", "go down", "quit"])
        Session(io=io, world=world).run()
        assert world.current_room == "hangar_deck"


def test_storage_bay_visible_at_high_cylon_vibes():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Believer", "hangar_deck")
        world.visited_rooms.append("hangar_deck")
        set_stat(world, "cylon_vibes", 55)
        io = ScriptedIO(["go down", "quit"])
        Session(io=io, world=world).run()
        assert world.current_room == "storage_bay"


# ─── Items & misc ─────────────────────────────────────────────────────────────


def test_photo_examine_spikes_suspicion_hard():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Snoop", "adamas_quarters")
        world.visited_rooms.append("adamas_quarters")
        world.flags["entered_adamas_quarters"] = True  # skip the witness bump
        before = get_stat(world, "suspicion")
        io = ScriptedIO(
            ["examine drawer", "take photograph", "examine photograph", "quit"]
        )
        Session(io=io, world=world).run()
        after = get_stat(world, "suspicion")
        assert "photo_academy" in world.inventory
        assert after - before >= 15  # hard spike


def test_cylon_detector_use_produces_a_beep():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Tester", "baltars_lab")
        world.visited_rooms.append("baltars_lab")
        world.flags["baltar_distracted"] = True  # so we can grab the detector
        io = ScriptedIO(["take detector", "use detector", "quit"])
        Session(io=io, world=world).run()
        t = io.transcript.lower()
        assert "beep" in t


def test_triad_cards_pickup():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Player", "pilots_rec")
        world.visited_rooms.append("pilots_rec")
        io = ScriptedIO(["take cards", "quit"])
        Session(io=io, world=world).run()
        assert "triad_cards" in world.inventory


def test_scrolls_pickup_and_examine_calls_pythia_a_hack():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Reader", "sickbay")
        world.visited_rooms.append("sickbay")
        io = ScriptedIO(["take scrolls", "examine scrolls", "quit"])
        Session(io=io, world=world).run()
        assert "scrolls" in world.inventory
        assert "hack" in io.transcript.lower()


# ─── Sealed envelope: a fourth (fifth?) ending ────────────────────────────────


def test_sealed_envelope_pickup_and_open_triggers_forbidden_knowledge_ending():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Curious", "cic")
        world.visited_rooms.append("cic")
        io = ScriptedIO(["take envelope", "use envelope", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("__ended__") == "forbidden_knowledge"
        assert "FORBIDDEN KNOWLEDGE" in io.transcript


def test_sealed_envelope_examine_shows_DO_NOT_OPEN_warning():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Tempted", "cic")
        world.visited_rooms.append("cic")
        io = ScriptedIO(["examine envelope", "quit"])
        Session(io=io, world=world).run()
        assert "DO NOT OPEN" in io.transcript
