from dataclasses import asdict, dataclass, field
from typing import Any

from .registry import ROOMS

SAVE_VERSION = "0.1"


@dataclass
class WorldState:
    player_name: str = ""
    current_room: str = ""
    inventory: list[str] = field(default_factory=list)
    room_items: dict[str, list[str]] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)
    turn: int = 0
    npc_state: dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["version"] = SAVE_VERSION
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "WorldState":
        d = dict(d)
        d.pop("version", None)
        return cls(**d)


def new_world(player_name: str, starting_room: str) -> WorldState:
    """Initialize a fresh WorldState from current registry contents."""
    world = WorldState(player_name=player_name, current_room=starting_room)
    for room in ROOMS.values():
        world.room_items[room.id] = list(room.items)
    return world


def items_in_room(world: WorldState, room_id: str) -> list[str]:
    return world.room_items.get(room_id, [])


def move_item_to_inventory(world: WorldState, item_id: str) -> None:
    for items in world.room_items.values():
        if item_id in items:
            items.remove(item_id)
    if item_id not in world.inventory:
        world.inventory.append(item_id)


def move_item_to_room(world: WorldState, item_id: str, room_id: str) -> None:
    if item_id in world.inventory:
        world.inventory.remove(item_id)
    for items in world.room_items.values():
        if item_id in items:
            items.remove(item_id)
    world.room_items.setdefault(room_id, []).append(item_id)
