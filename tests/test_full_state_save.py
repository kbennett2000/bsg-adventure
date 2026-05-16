"""Full WorldState round-trip test.

Verifies that EVERY mutable field on WorldState (plus the achievements file
and NG+ carryover) round-trips cleanly through save → mutate → load.

Note: time, schedules, IS_CYLON, resurrection_count are NOT implemented in
this codebase and therefore are not tested here. See BALANCE.md.
"""

import dataclasses
import json
import os
import tempfile

import content  # noqa: F401
from engine import save as save_module
from engine.io import ScriptedIO
from engine.session import Session
from engine.world import WorldState, bump_stat, get_stat, new_world, set_stat


def _fill_every_field(world: WorldState) -> None:
    """Mutate every documented field on WorldState to a non-default value
    that we can verify after a save/load cycle."""
    world.player_name = "FullState"
    world.current_room = "cic"
    world.inventory = ["mop", "napkin", "canteen", "flask", "triad_cards"]
    world.room_items = {
        "env_control": ["bunk", "console", "locker"],
        "head_deck_5": ["scrolls"],
        "corridor_c12": ["sealed_envelope"],
    }
    world.flags = {
        # opening
        "seen_intercom_page": True,
        "got_canteen": True,
        "realized_napkin_is_coords": True,
        "entered_head": True,
        "entered_cic": True,
        # stash quest
        "found_flask": True,
        "found_stash_mess": True,
        "found_stash_hangar": True,
        "quest_stash_complete": True,
        # wrench quest
        "baltar_distracted": True,
        "quest_wrench_complete": True,
        "found_academy_photo": True,
        # cards quest
        "quest_cards_started": True,
        "quest_cards_resolved": True,
        "quest_cards_choice": "accuse",
        # prophecy quest
        "quest_prophecy_started": True,
        "quest_prophecy_resolved": True,
        "quest_prophecy_choice": "yes",
        # other
        "mystery_meat_solved": True,
        "examined_academy_photo": True,
        "opened_envelope": False,
        "baltar_thinks_you_see_her": True,
        "baltar_thinks_you_know": False,
        # romance state
        "active_romances": ["six", "helo"],
        "romance_starbuck": 4,
        "romance_six": 2,
        "romance_helo": 1,
        "romance_dualla": 0,
        # frak count, achievement adjacencies
        "__frak_index__": 47,
        "tigh_drink_count": 3,
        "dignity_lost": 12,
        # encounter one-shot flags (post-balance)
        "c12_encounter_seen_six_walks": True,
        "b7_encounter_seen_tigh_catwalk": True,
        # NG+ carryover
        "ng_plus": True,
        "ng_plus_count": 2,
        "previous_ending": "spaced",
        # witness one-shots
        "witnessed_tigh_drinking": True,
        "witnessed_command_meeting": True,
        "witnessed_baltar_solo_argument": True,
    }
    world.turn = 73
    world.npc_state = {
        "tigh": {"wrong_name_index": 5},
        "hadrian": {"rumor_index": 4, "told_about_xo": True, "ng_plus_acknowledged": True},
        "adama": {"proverb_index": 7, "ng_plus_acknowledged": True},
        "starbuck": {"mood_index": 3},
        "apollo": {"memory_index": 2},
        "baltar": {"paranoia": 2, "co_conspirator": True},
        "six": {"ng_plus_acknowledged": True},
        "boomer": {"prompt_index": 3},
        "corridor_c12": {"last_encounter": "baltar_argues"},
        "corridor_b": {"last_encounter": "six_supervisor"},
    }
    world.visited_rooms = [
        "env_control", "corridor_c12", "head_deck_5", "mess_hall",
        "corridor_b", "corridor_a", "cic", "sickbay", "adamas_quarters",
        "hangar_deck", "pilots_rec", "baltars_lab", "brig", "observation_deck",
    ]
    world.stats = {
        "morale": 78,
        "suspicion": 41,
        "cylon_vibes": 67,
        "exhaustion": 22,
    }


def test_world_state_has_no_undocumented_fields():
    """Sanity check: WorldState's field set is what we expect. If a new field
    is added without updating this test, the failure flags the need to also
    update the save round-trip assertions."""
    world = new_world("X", "env_control")
    field_names = {f.name for f in dataclasses.fields(world)}
    expected = {
        "player_name", "current_room", "inventory", "room_items",
        "flags", "turn", "npc_state", "visited_rooms", "stats",
    }
    assert field_names == expected, (
        f"WorldState fields changed. Got {field_names}; "
        f"update this test and full-state-save coverage. Expected {expected}."
    )


def test_full_world_state_round_trips_through_save_load():
    """Save → load → assert every WorldState field is identical."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        original = new_world("FullState", "env_control")
        _fill_every_field(original)

        save_module.save_world(original, slot="default")
        loaded = save_module.load_world("FullState", "default")

        for field in dataclasses.fields(WorldState):
            orig_val = getattr(original, field.name)
            loaded_val = getattr(loaded, field.name)
            assert orig_val == loaded_val, (
                f"field {field.name!r} did not round-trip:\n"
                f"  saved   = {orig_val!r}\n"
                f"  loaded  = {loaded_val!r}"
            )


def test_round_trip_after_mutation_via_session_loop():
    """End-to-end: run a real session that mutates state through gameplay,
    save mid-stream, load fresh, assert state is preserved."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        # First session: do real things that touch lots of state.
        world = new_world("Player1", "env_control")
        io = ScriptedIO(
            [
                "take mop",                            # inventory mutation
                "use mop",                              # stats mutation (morale, sus, ex)
                "talk to hadrian",                     # npc_state.hadrian
                "talk to hadrian about jump",          # flag
                "go east", "go east",                  # current_room, visited_rooms, room_items spawn
                "talk to tigh",                        # multiple mutations
                "examine floor",                       # spawns napkin
                "take napkin",
                "frak", "frak", "frak",                # __frak_index__
                "save before_load",
                "quit",
            ]
        )
        Session(io=io, world=world).run()

        # Snapshot the expected state from world1
        snapshot = {f.name: getattr(world, f.name) for f in dataclasses.fields(WorldState)}

        # Second session: brand-new world, then load.
        fresh = new_world("Player1", "env_control")
        io2 = ScriptedIO(["load before_load", "quit"])
        Session(io=io2, world=fresh).run()

        # Every field on the freshly-loaded world should equal the snapshot.
        for field_name, expected in snapshot.items():
            actual = getattr(fresh, field_name)
            assert actual == expected, (
                f"after load, {field_name!r} differs:\n"
                f"  expected = {expected!r}\n"
                f"  got      = {actual!r}"
            )


def test_stats_round_trip_explicitly_for_every_stat():
    """All four hidden stats round-trip with non-default values."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Statty", "env_control")
        set_stat(world, "morale", 13)
        set_stat(world, "suspicion", 91)
        set_stat(world, "cylon_vibes", 64)
        set_stat(world, "exhaustion", 7)
        save_module.save_world(world, slot="default")

        loaded = save_module.load_world("Statty", "default")
        assert loaded.stats["morale"] == 13
        assert loaded.stats["suspicion"] == 91
        assert loaded.stats["cylon_vibes"] == 64
        assert loaded.stats["exhaustion"] == 7


def test_romance_state_round_trips_completely():
    """Romance flags, active_romances list, complicated terminals."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Romancer", "env_control")
        world.flags["active_romances"] = ["six", "helo"]
        world.flags["romance_starbuck"] = 4   # complicated (terminal)
        world.flags["romance_six"] = 2
        world.flags["romance_helo"] = 1
        world.flags["romance_dualla"] = 0
        save_module.save_world(world, slot="default")

        loaded = save_module.load_world("Romancer", "default")
        assert loaded.flags["active_romances"] == ["six", "helo"]
        assert loaded.flags["romance_starbuck"] == 4
        assert loaded.flags["romance_six"] == 2
        assert loaded.flags["romance_helo"] == 1
        assert loaded.flags["romance_dualla"] == 0


def test_ng_plus_carryover_round_trips():
    """NG+ flags: ng_plus, ng_plus_count, previous_ending."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Wheel", "env_control")
        world.flags["ng_plus"] = True
        world.flags["ng_plus_count"] = 5
        world.flags["previous_ending"] = "forbidden_knowledge"
        save_module.save_world(world, slot="default")

        loaded = save_module.load_world("Wheel", "default")
        assert loaded.flags["ng_plus"] is True
        assert loaded.flags["ng_plus_count"] == 5
        assert loaded.flags["previous_ending"] == "forbidden_knowledge"


def test_achievements_file_persists_independently_of_world_save():
    """Achievements live in their own file at <save_dir>/<player>/achievements.json,
    survive across world saves, and accumulate across sessions."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        from content.achievements import (
            load_unlocked, save_unlocked, check_and_unlock,
        )

        # Session 1: unlock so_say_we_all.
        save_unlocked("Persist", {"so_say_we_all"})
        # Session 2: simulate game-end that would unlock promotion_material.
        world = new_world("Persist", "env_control")
        world.flags["__ended__"] = "hero"
        set_stat(world, "suspicion", 0)
        new = check_and_unlock(world)
        new_ids = {a["id"] for a in new}
        # so_say_we_all already unlocked; only promotion_material newly fires.
        assert "promotion_material" in new_ids
        assert "so_say_we_all" not in new_ids

        # Both should be in the persisted file now.
        on_disk = load_unlocked("Persist")
        assert "so_say_we_all" in on_disk
        assert "promotion_material" in on_disk


def test_room_items_round_trip_with_complex_arrangement():
    """room_items reflects items the player has rearranged. Verify the exact
    mapping is preserved across save/load."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        from engine.world import move_item_to_inventory, move_item_to_room
        world = new_world("Mover", "env_control")
        # Mover takes the mop, drops it elsewhere.
        move_item_to_inventory(world, "mop")
        move_item_to_room(world, "mop", "head_deck_5")
        # Save the state.
        save_module.save_world(world, slot="default")
        # Load and verify.
        loaded = save_module.load_world("Mover", "default")
        assert "mop" not in loaded.inventory
        assert "mop" in loaded.room_items["head_deck_5"]
        assert "mop" not in loaded.room_items["env_control"]


def test_npc_state_complex_nested_round_trips():
    """NPCs accumulate per-NPC state via npc_state. Each NPC's dict should
    survive intact."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("NpcStateTester", "env_control")
        world.npc_state = {
            "tigh": {"wrong_name_index": 6, "suspicion": 50, "stash_returned": 2},
            "hadrian": {"rumor_index": 5, "told_about_xo": True},
            "adama": {"proverb_index": 4},
            "starbuck": {"mood_index": 2},
            "boomer": {"prompt_index": 1},
            "corridor_c12": {"last_encounter": "six_walks"},
        }
        save_module.save_world(world, slot="default")
        loaded = save_module.load_world("NpcStateTester", "default")
        assert loaded.npc_state == world.npc_state


def test_save_file_is_human_readable_json():
    """Sanity check: the on-disk format is intact JSON we can decode."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Reader", "env_control")
        save_module.save_world(world, slot="default")
        from pathlib import Path
        save_path = Path(tmp) / "Reader" / "default.json"
        raw = save_path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert parsed["player_name"] == "Reader"
        assert parsed["current_room"] == "env_control"
        assert "stats" in parsed
        assert parsed["version"]   # versioned for migrations
