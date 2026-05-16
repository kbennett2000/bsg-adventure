"""End-to-end smoke test: drive the game with scripted input and confirm the
opening quest flow actually works. Stdlib-only — no pytest."""

import os
import tempfile

import content  # noqa: F401  — register everything
from engine.io import ScriptedIO
from engine.session import Session
from engine.world import new_world


def _run(inputs, player_name="Tester", save_dir=None):
    if save_dir is not None:
        os.environ["BSG_SAVE_DIR"] = save_dir
    world = new_world(player_name, "env_control")
    io = ScriptedIO(inputs)
    Session(io=io, world=world).run()
    return io, world


def test_opening_room_renders():
    io, world = _run(["quit"])
    t = io.transcript
    assert "ENVIRONMENTAL CONTROL" in t
    assert "Crewman Hadrian" in t
    assert "INTERCOM" in t  # the page fires on entry


def test_can_examine_things_in_room():
    io, world = _run(["examine console", "examine locker", "examine algae bar", "quit"])
    t = io.transcript.lower()
    assert "console" in t
    assert "locker" in t
    assert "algae" in t


def test_inventory_starts_empty():
    io, world = _run(["inventory", "quit"])
    assert "nothing" in io.transcript.lower() or "weight of expectation" in io.transcript


def test_pick_up_mop():
    io, world = _run(["take mop", "inventory", "quit"])
    assert "mop" in world.inventory, f"inventory was {world.inventory}"
    assert "regulation mop" in io.transcript


def test_quest_flow_get_canteen_from_tigh():
    with tempfile.TemporaryDirectory() as tmp:
        io, world = _run(
            [
                "use console",            # set noticed_anomaly flag
                "talk to hadrian",        # gossip
                "talk to hadrian about xo",
                "go east",                # corridor C-12
                "go east",                # the head
                "talk to tigh",           # quest given, canteen received
                "inventory",
                "quit",
            ],
            save_dir=tmp,
        )
        t = io.transcript
        assert world.flags.get("noticed_anomaly") is True, "console should set anomaly flag"
        assert world.flags.get("got_canteen") is True, "Tigh should hand over the canteen"
        assert "canteen" in world.inventory, f"canteen should be in inventory: {world.inventory}"
        assert world.current_room == "head_deck_5"
        assert "frak" in t.lower()
        assert "tide of command" in t.lower(), "Tigh's signature line should fire"
        assert "brass handle" in t.lower(), "quest instruction should mention brass handle"


def test_tigh_forgets_player_name():
    with tempfile.TemporaryDirectory() as tmp:
        io, world = _run(
            [
                "go east",
                "go east",
                "talk to tigh",   # first encounter, advances wrong-name index twice (first+dismiss)
                "talk to tigh",   # second encounter (reminder), still doesn't use real name
                "quit",
            ],
            save_dir=tmp,
        )
        # Tigh's first encounter calls _tigh_next_wrong_name twice (greeting + dismiss)
        assert world.npc_state.get("tigh", {}).get("wrong_name_index", 0) >= 2


def test_save_and_load_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        # First session: get the canteen, then save
        io1, world1 = _run(
            [
                "go east",
                "go east",
                "talk to tigh",
                "save mid_quest",
                "quit",
            ],
            player_name="Saver",
            save_dir=tmp,
        )
        assert "canteen" in world1.inventory
        assert world1.flags.get("got_canteen") is True

        # Second session: fresh world for the same player, then `load` command
        os.environ["BSG_SAVE_DIR"] = tmp
        fresh = new_world("Saver", "env_control")
        io2 = ScriptedIO(["load mid_quest", "inventory", "quit"])
        Session(io=io2, world=fresh).run()
        assert "canteen" in fresh.inventory, f"after load: inventory={fresh.inventory}"
        assert fresh.current_room == "head_deck_5"
        assert fresh.flags.get("got_canteen") is True


def test_unknown_verb_is_in_character():
    io, world = _run(["frizzle the bargle", "quit"])
    t = io.transcript.lower()
    assert "frak" in t or "specialist" in t or "mop" in t


def test_frak_is_free_turn():
    io, world = _run(["frak", "frak", "frak", "quit"])
    assert world.turn == 0, f"frak should not advance turn, got turn={world.turn}"


def test_salute_advances_turn_and_costs_dignity():
    io, world = _run(["salute", "salute", "quit"])
    assert world.flags.get("dignity_lost", 0) == 2
    assert world.turn == 2


def test_corridor_encounter_state_tracked():
    with tempfile.TemporaryDirectory() as tmp:
        io, world = _run(
            ["go east", "go west", "go east", "quit"],
            save_dir=tmp,
        )
        # confirm at least one corridor encounter fired and was recorded
        assert world.npc_state.get("corridor_c12", {}).get("last_encounter") is not None
