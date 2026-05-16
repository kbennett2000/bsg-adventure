"""Save/load tests. Stdlib-only — no pytest."""

import os
import tempfile

import content  # noqa: F401  — registers rooms/npcs/items
from engine import save
from engine.world import new_world


def test_safe_name():
    assert save.is_safe_name("kara")
    assert save.is_safe_name("kara_thrace")
    assert save.is_safe_name("Six6")
    assert not save.is_safe_name("kara/thrace")
    assert not save.is_safe_name("../etc/passwd")
    assert not save.is_safe_name("")
    assert not save.is_safe_name("a" * 33)


def test_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        try:
            world = new_world("starbuck", "env_control")
            world.flags["got_canteen"] = True
            world.inventory.append("canteen")
            world.turn = 42

            save.save_world(world, slot="default")
            assert save.has_save("starbuck", "default")

            loaded = save.load_world("starbuck", "default")
            assert loaded.player_name == "starbuck"
            assert loaded.current_room == "env_control"
            assert loaded.flags["got_canteen"] is True
            assert "canteen" in loaded.inventory
            assert loaded.turn == 42
        finally:
            os.environ.pop("BSG_SAVE_DIR", None)


def test_atomic_write_no_tmp_left():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        try:
            world = new_world("apollo", "env_control")
            save.save_world(world, slot="auto")
            from pathlib import Path
            save_dir = Path(tmp) / "apollo"
            files = list(save_dir.iterdir())
            assert all(f.name == "auto.json" for f in files), f"unexpected files: {files}"
        finally:
            os.environ.pop("BSG_SAVE_DIR", None)


def test_rejects_unsafe_slot():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        try:
            world = new_world("kara", "env_control")
            try:
                save.save_world(world, slot="../escape")
            except ValueError:
                return
            assert False, "should have raised ValueError"
        finally:
            os.environ.pop("BSG_SAVE_DIR", None)


def test_save_survives_overwrite():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        try:
            world = new_world("hadrian", "env_control")
            world.turn = 1
            save.save_world(world, slot="auto")
            world.turn = 99
            save.save_world(world, slot="auto")
            loaded = save.load_world("hadrian", "auto")
            assert loaded.turn == 99
        finally:
            os.environ.pop("BSG_SAVE_DIR", None)
