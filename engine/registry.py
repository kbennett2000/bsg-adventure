from .models import Item, NPC, Room

ROOMS: dict[str, Room] = {}
NPCS: dict[str, NPC] = {}
ITEMS: dict[str, Item] = {}


def register_room(room: Room) -> None:
    ROOMS[room.id] = room


def register_npc(npc: NPC) -> None:
    NPCS[npc.id] = npc


def register_item(item: Item) -> None:
    ITEMS[item.id] = item


def reset() -> None:
    """Test-only: clear all registries. Re-import content modules to repopulate."""
    ROOMS.clear()
    NPCS.clear()
    ITEMS.clear()
