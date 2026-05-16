from dataclasses import asdict, dataclass, field
from typing import Any

from .registry import ROOMS

SAVE_VERSION = "0.1"


# ─── Watch-cycle clock ─────────────────────────────────────────────────────────

SHIFT_NAMES = [
    "Morning Watch",   # 0
    "Forenoon",        # 1
    "Afternoon",       # 2
    "Dog Watch",       # 3
    "Night",           # 4
]
SHIFT_COUNT = len(SHIFT_NAMES)
TURNS_PER_SHIFT = 15


def shift_name(world: "WorldState") -> str:
    return SHIFT_NAMES[world.shift % SHIFT_COUNT]


def advance_shift(world: "WorldState", count: int = 1) -> bool:
    """Advance the watch clock by `count` shifts. Resets the per-shift turn
    counter. Returns True if the day rolled over (one or more times)."""
    day_rolled = False
    for _ in range(count):
        world.shift = (world.shift + 1) % SHIFT_COUNT
        if world.shift == 0:
            world.day += 1
            day_rolled = True
    world.turns_this_shift = 0
    return day_rolled


def tick_shift_counter(world: "WorldState") -> bool:
    """Increment the per-shift counter; if it reaches TURNS_PER_SHIFT, advance.
    Returns True if a shift advance happened (caller can render a banner)."""
    world.turns_this_shift += 1
    if world.turns_this_shift >= TURNS_PER_SHIFT:
        advance_shift(world, 1)
        return True
    return False


@dataclass
class WorldState:
    player_name: str = ""
    current_room: str = ""
    inventory: list[str] = field(default_factory=list)
    room_items: dict[str, list[str]] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)
    turn: int = 0
    npc_state: dict[str, dict] = field(default_factory=dict)
    visited_rooms: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=lambda: {
        "morale": 50,
        "suspicion": 0,
        "cylon_vibes": 0,
        "exhaustion": 0,
    })
    # Watch-cycle clock. 0..4 maps to MORNING_WATCH / FORENOON / AFTERNOON /
    # DOG_WATCH / NIGHT. `day` increments on each NIGHT → MORNING_WATCH wrap.
    # `turns_this_shift` is the per-shift counter; at TURNS_PER_SHIFT (15) it
    # auto-advances the shift.
    shift: int = 0
    day: int = 1
    turns_this_shift: int = 0

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


# ─── stats ──────────────────────────────────────────────────────────────────────


STAT_NAMES = ("morale", "suspicion", "cylon_vibes", "exhaustion")


def _ensure_stats(world: WorldState) -> None:
    """Back-compat for older saves that didn't have stats."""
    if not world.stats:
        world.stats = {"morale": 50, "suspicion": 0, "cylon_vibes": 0, "exhaustion": 0}
    for k, default in (("morale", 50), ("suspicion", 0), ("cylon_vibes", 0), ("exhaustion", 0)):
        world.stats.setdefault(k, default)


def get_stat(world: WorldState, name: str) -> int:
    _ensure_stats(world)
    return world.stats.get(name, 0)


def bump_stat(world: WorldState, name: str, amount: int) -> int:
    """Adjust a stat with clamping to [0, 100]. Returns the new value."""
    _ensure_stats(world)
    cur = world.stats.get(name, 0)
    new = max(0, min(100, cur + amount))
    world.stats[name] = new
    return new


def set_stat(world: WorldState, name: str, value: int) -> int:
    _ensure_stats(world)
    new = max(0, min(100, value))
    world.stats[name] = new
    return new


# Convenience: one-time witness events that bump a stat and set a flag so they
# don't fire repeatedly.
def witness_once(world: WorldState, flag: str, stat: str, amount: int) -> bool:
    """If `flag` is unset, bump `stat` by `amount` and set the flag. Returns True
    on first witness."""
    if world.flags.get(flag):
        return False
    world.flags[flag] = True
    bump_stat(world, stat, amount)
    return True
