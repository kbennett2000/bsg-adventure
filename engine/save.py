"""JSON save/load with atomic on-disk writes that survive host reboot."""

import json
import os
import re
from pathlib import Path

from .world import SAVE_VERSION, WorldState

_SAFE_NAME = re.compile(r"^[A-Za-z0-9_]{1,32}$")


def is_safe_name(name: str) -> bool:
    return bool(_SAFE_NAME.match(name))


def save_root() -> Path:
    env = os.environ.get("BSG_SAVE_DIR")
    if env:
        return Path(env)
    # Default: <repo>/saves, anchored to this file's location so working directory doesn't matter.
    return Path(__file__).resolve().parent.parent / "saves"


def _slot_path(player_name: str, slot: str) -> Path:
    if not is_safe_name(player_name):
        raise ValueError(f"invalid player name: {player_name!r}")
    if slot != "auto" and not _SAFE_NAME.match(slot):
        raise ValueError(f"invalid save slot: {slot!r}")
    return save_root() / player_name / f"{slot}.json"


def save_world(world: WorldState, slot: str = "auto") -> Path:
    """Atomic write: tmp + fsync + os.replace. Survives mid-save power loss."""
    path = _slot_path(world.player_name, slot)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(world.to_dict(), indent=2, sort_keys=True)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return path


def load_world(player_name: str, slot: str = "auto") -> WorldState:
    path = _slot_path(player_name, slot)
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    if d.get("version") != SAVE_VERSION:
        raise ValueError(
            f"save format version mismatch: file is {d.get('version')!r}, engine is {SAVE_VERSION!r}"
        )
    return WorldState.from_dict(d)


def has_save(player_name: str, slot: str = "auto") -> bool:
    try:
        return _slot_path(player_name, slot).exists()
    except ValueError:
        return False


def list_slots(player_name: str) -> list[str]:
    try:
        d = save_root() / player_name
    except ValueError:
        return []
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json"))
