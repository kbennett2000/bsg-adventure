from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Room:
    id: str
    name: str
    short_desc: str            # used on revisit
    long_desc: str             # used on first visit and explicit `look`
    exits: dict[str, str] = field(default_factory=dict)
    # Conditional exits: direction → (target_room_id, predicate(world) → bool).
    # Only shown / traversable when the predicate is True. Used for hidden rooms
    # that require an item or a stat threshold to perceive.
    hidden_exits: dict[str, tuple] = field(default_factory=dict)
    items: list[str] = field(default_factory=list)
    npcs: list[str] = field(default_factory=list)
    on_enter: Optional[Callable] = None  # fires every entry; gate one-shots with flags
    on_examine: dict[str, str] = field(default_factory=dict)


@dataclass
class NPC:
    id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    on_talk: Optional[Callable] = None
    on_give: dict[str, Callable] = field(default_factory=dict)  # item_id → callable(world)


@dataclass
class Item:
    id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    takeable: bool = True
    on_use: Optional[Callable] = None
    on_eat: Optional[Callable] = None
    on_drink: Optional[Callable] = None
    # Targeted-use handlers: keyed by target id. `use mop on locker` dispatches
    # through this dict if the mop registered a handler for "locker". Falls
    # through to the canned "nothing happens" line otherwise.
    on_use_with: dict[str, Callable] = field(default_factory=dict)
