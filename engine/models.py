from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Room:
    id: str
    name: str
    short_desc: str
    long_desc: str
    exits: dict[str, str] = field(default_factory=dict)
    items: list[str] = field(default_factory=list)
    npcs: list[str] = field(default_factory=list)
    on_enter: Optional[Callable] = None
    on_examine: dict[str, str] = field(default_factory=dict)


@dataclass
class NPC:
    id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    on_talk: Optional[Callable] = None


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
