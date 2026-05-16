"""Verb handlers. Each takes (world, command, session) and returns a HandlerResult."""

from dataclasses import dataclass
from random import choice
from typing import Callable, Optional

from . import save as save_module
from .models import Item, NPC, Room
from .parser import Command
from .registry import ITEMS, NPCS, ROOMS
from .world import (
    WorldState,
    items_in_room,
    move_item_to_inventory,
    move_item_to_room,
)


@dataclass
class HandlerResult:
    text: str = ""
    advance_turn: bool = True
    quit: bool = False
    ended: bool = False  # game-over (ending triggered); session loop should exit after printing


def trigger_ending(world: "WorldState", ending_id: str, text: str) -> HandlerResult:
    world.flags["__ended__"] = ending_id
    return HandlerResult(text=text, ended=True, advance_turn=False)


UNKNOWN_VERB_REPLIES = [
    "Frak if I know what that means, specialist.",
    "You can't frakking do that, Specialist.",
    "Try mopping instead. You're good at mopping.",
    "That ain't a real word down here on deck five.",
    "What in the cosmic frak are you on about?",
]

NOTHING_HERE_REPLIES = [
    "You don't see any \"{obj}\" here, specialist.",
    "There's no \"{obj}\" to be found. Look harder. Or don't.",
    "Whatever a \"{obj}\" is, it ain't on this deck.",
]


# ─── object resolution ─────────────────────────────────────────────────────────


def _matches(query: str, thing) -> bool:
    q = query.lower().strip()
    name = thing.name.lower()
    aliases = [a.lower() for a in getattr(thing, "aliases", [])]
    if q == name or q in aliases:
        return True
    if q in name:
        return True
    for a in aliases:
        if q in a:
            return True
    return False


def _resolve_in_room_items(query: str, world: WorldState) -> Optional[Item]:
    for item_id in items_in_room(world, world.current_room):
        if _matches(query, ITEMS[item_id]):
            return ITEMS[item_id]
    return None


def _resolve_in_inventory(query: str, world: WorldState) -> Optional[Item]:
    for item_id in world.inventory:
        if _matches(query, ITEMS[item_id]):
            return ITEMS[item_id]
    return None


def _resolve_npc(query: str, world: WorldState) -> Optional[NPC]:
    room = ROOMS[world.current_room]
    for npc_id in room.npcs:
        if _matches(query, NPCS[npc_id]):
            return NPCS[npc_id]
    return None


def _resolve_any(query: str, world: WorldState):
    return (
        _resolve_in_room_items(query, world)
        or _resolve_npc(query, world)
        or _resolve_in_inventory(query, world)
    )


# ─── helpers ───────────────────────────────────────────────────────────────────


def describe_room(world: WorldState, first_visit: bool = False) -> str:
    room = ROOMS[world.current_room]
    body = room.long_desc if (first_visit or not room.short_desc) else room.short_desc
    parts = [f"── {room.name.upper()} ──", "", body]
    room_items = items_in_room(world, room.id)
    if room_items:
        names = [ITEMS[i].name for i in room_items]
        parts += ["", "You see: " + ", ".join(names) + "."]
    if room.npcs:
        names = [_visible_npc_name(world, n) for n in room.npcs if _npc_visible(world, n)]
        if names:
            parts += ["", "Present: " + ", ".join(names) + "."]
    if room.exits:
        parts += ["", "Exits: " + ", ".join(sorted(room.exits.keys())) + "."]
    return "\n".join(parts)


def _npc_visible(world: WorldState, npc_id: str) -> bool:
    """NPCs can be conditionally hidden via flags (e.g., 'npc_hidden_six')."""
    return not world.flags.get(f"npc_hidden_{npc_id}", False)


def _visible_npc_name(world: WorldState, npc_id: str) -> str:
    return NPCS[npc_id].name


# ─── handlers ──────────────────────────────────────────────────────────────────


def cmd_look(world, command, session) -> HandlerResult:
    if command.obj:
        thing = _resolve_any(command.obj, world)
        if thing is None:
            return HandlerResult(text=choice(NOTHING_HERE_REPLIES).format(obj=command.obj), advance_turn=False)
        return HandlerResult(text=_resolve_description(thing, world), advance_turn=False)
    # explicit `look` always shows the long form
    return HandlerResult(text=describe_room(world, first_visit=True), advance_turn=False)


def cmd_examine(world, command, session) -> HandlerResult:
    if not command.obj:
        return HandlerResult(text="Examine what? Use your eyes, specialist.", advance_turn=False)
    # Try room-specific on_examine first (for non-item scenery like 'stall', 'mirror')
    room = ROOMS[world.current_room]
    obj_norm = command.obj.lower()
    for key, response in room.on_examine.items():
        if obj_norm == key.lower() or obj_norm in key.lower() or key.lower() in obj_norm:
            return HandlerResult(text=response if isinstance(response, str) else response(world), advance_turn=False)
    thing = _resolve_any(command.obj, world)
    if thing is None:
        return HandlerResult(text=choice(NOTHING_HERE_REPLIES).format(obj=command.obj), advance_turn=False)
    desc = _resolve_description(thing, world)
    return HandlerResult(text=desc, advance_turn=False)


def _resolve_description(thing, world) -> str:
    """Allow items/NPCs to provide a dynamic description via a `_dynamic_description`
    attribute (callable taking world). Falls back to the static `description` field."""
    dyn = getattr(thing, "_dynamic_description", None)
    if callable(dyn):
        return dyn(world)
    return thing.description


def cmd_go(world, command, session) -> HandlerResult:
    if not command.obj:
        return HandlerResult(text="Go where? Pick a direction, specialist.", advance_turn=False)
    direction = command.obj.lower().strip()
    room = ROOMS[world.current_room]
    if direction not in room.exits:
        return HandlerResult(text=f"There's no way {direction} from here. The bulkhead disagrees with you.", advance_turn=False)
    new_id = room.exits[direction]
    world.current_room = new_id
    new_room = ROOMS[new_id]
    first_visit = new_id not in world.visited_rooms
    if first_visit:
        world.visited_rooms.append(new_id)
    text = describe_room(world, first_visit=first_visit)
    if new_room.on_enter:
        extra = new_room.on_enter(world)
        if extra:
            text += "\n\n" + extra
    return HandlerResult(text=text)


def cmd_take(world, command, session) -> HandlerResult:
    if not command.obj:
        return HandlerResult(text="Take what?", advance_turn=False)
    item = _resolve_in_room_items(command.obj, world)
    if item is None:
        return HandlerResult(text=f"There's no \"{command.obj}\" here to take.", advance_turn=False)
    if not item.takeable:
        return HandlerResult(text=f"The {item.name} isn't going anywhere with you, specialist. Bolted, sacred, or both.", advance_turn=False)
    move_item_to_inventory(world, item.id)
    return HandlerResult(text=f"You take the {item.name}.")


def cmd_drop(world, command, session) -> HandlerResult:
    if not command.obj:
        return HandlerResult(text="Drop what?", advance_turn=False)
    item = _resolve_in_inventory(command.obj, world)
    if item is None:
        return HandlerResult(text=f"You're not carrying any \"{command.obj}\".", advance_turn=False)
    move_item_to_room(world, item.id, world.current_room)
    return HandlerResult(text=f"You drop the {item.name}.")


def cmd_inventory(world, command, session) -> HandlerResult:
    if not world.inventory:
        return HandlerResult(text="You're carrying nothing but the weight of expectation.", advance_turn=False)
    names = [ITEMS[i].name for i in world.inventory]
    return HandlerResult(text="You're carrying: " + ", ".join(names) + ".", advance_turn=False)


def cmd_talk(world, command, session) -> HandlerResult:
    if not command.obj:
        return HandlerResult(text="Talk to whom, specialist? The bulkhead?", advance_turn=False)
    npc = _resolve_npc(command.obj, world)
    if npc is None:
        return HandlerResult(text=f"There's nobody here named \"{command.obj}\". The silence is loud.", advance_turn=False)
    if npc.on_talk is None:
        return HandlerResult(text=f"{npc.name} stares through you like glass.")
    result = npc.on_talk(world, command.target)
    # NPC dialogue can either return a plain string (normal case) or a HandlerResult (ending trigger).
    if isinstance(result, HandlerResult):
        return result
    return HandlerResult(text=result)


def cmd_use(world, command, session) -> HandlerResult:
    if not command.obj:
        return HandlerResult(text="Use what?", advance_turn=False)
    item = _resolve_in_inventory(command.obj, world) or _resolve_in_room_items(command.obj, world)
    if item is None:
        return HandlerResult(text=f"You don't have any \"{command.obj}\" to use.", advance_turn=False)
    if command.target:
        # "use X on Y" — for the slice we only support generic on_use; targeted use can come later
        return HandlerResult(text=f"You wave the {item.name} vaguely at the {command.target}. Nothing happens. You feel watched.")
    if item.on_use is None:
        return HandlerResult(text=f"You can't think of anything productive to do with the {item.name} right now.")
    return HandlerResult(text=item.on_use(world))


def cmd_give(world, command, session) -> HandlerResult:
    if not command.obj or not command.target:
        return HandlerResult(text="Give what to whom? Use the form: give <item> to <person>.", advance_turn=False)
    item = _resolve_in_inventory(command.obj, world)
    if item is None:
        return HandlerResult(text=f"You don't have any \"{command.obj}\" to give.", advance_turn=False)
    npc = _resolve_npc(command.target, world)
    if npc is None:
        return HandlerResult(text=f"There's no \"{command.target}\" here to give it to.", advance_turn=False)
    if item.id in npc.on_give:
        result = npc.on_give[item.id](world)
        if isinstance(result, HandlerResult):
            return result
        return HandlerResult(text=result)
    return HandlerResult(text=f"You hold out the {item.name}. {npc.name} does not appear to register your existence.")


def cmd_wait(world, command, session) -> HandlerResult:
    return HandlerResult(text="You stand there. Time advances. The ship hums. Somewhere, an officer sighs meaningfully.")


def cmd_save(world, command, session) -> HandlerResult:
    slot = (command.obj or "default").strip().split()[0] if command.obj else "default"
    if not save_module.is_safe_name(slot):
        return HandlerResult(text=f"\"{slot}\" is not a valid slot name. Letters, numbers, underscores. Up to 32.", advance_turn=False)
    try:
        path = save_module.save_world(world, slot)
    except Exception as exc:
        return HandlerResult(text=f"Save failed: {exc}", advance_turn=False)
    return HandlerResult(text=f"Saved to slot '{slot}'. ({path})", advance_turn=False)


def cmd_load(world, command, session) -> HandlerResult:
    slot = (command.obj or "default").strip().split()[0] if command.obj else "default"
    if not save_module.is_safe_name(slot):
        return HandlerResult(text=f"\"{slot}\" is not a valid slot name.", advance_turn=False)
    if not save_module.has_save(world.player_name, slot):
        return HandlerResult(text=f"No save in slot '{slot}' for {world.player_name}.", advance_turn=False)
    try:
        loaded = save_module.load_world(world.player_name, slot)
    except Exception as exc:
        return HandlerResult(text=f"Load failed: {exc}", advance_turn=False)
    # Mutate the current world in place so session retains the same reference
    for attr in ("player_name", "current_room", "inventory", "room_items", "flags", "turn", "npc_state"):
        setattr(world, attr, getattr(loaded, attr))
    return HandlerResult(text=f"Loaded slot '{slot}'.\n\n" + describe_room(world), advance_turn=False)


def cmd_help(world, command, session) -> HandlerResult:
    text = (
        "Things you can say, specialist:\n"
        "  look                       — describe where you are\n"
        "  examine <thing>            — get a closer look (also: x)\n"
        "  go <direction>             — north/south/east/west/up/down (also: n, s, e, w)\n"
        "  take <item> / drop <item>  — manage your stuff\n"
        "  inventory                  — what you're carrying (also: i)\n"
        "  talk to <person>           — start a conversation\n"
        "  talk to <person> about <X> — ask about something specific\n"
        "  use <item>                 — interact with an item\n"
        "  give <item> to <person>    — hand something over\n"
        "  drink <item>               — drink something. Be careful what.\n"
        "  eat <item>                 — eat something. Same warning.\n"
        "  wait                       — let a turn pass\n"
        "  save [slot] / load [slot]  — save your game / load it back\n"
        "  salute                     — render proper respect (or don't)\n"
        "  frak                       — express yourself. Free turn.\n"
        "  quit                       — leave the ship\n"
    )
    return HandlerResult(text=text, advance_turn=False)


def cmd_quit(world, command, session) -> HandlerResult:
    return HandlerResult(text="Frak out, specialist.", quit=True, advance_turn=False)


# ─── flavor verbs ──────────────────────────────────────────────────────────────

SALUTE_REPLIES = [
    "You snap to. Nobody salutes back. Nobody looks. Your hand returns to its post in shame.",
    "Crisp. Textbook. The bulkhead does not return your salute. Dignity -1.",
    "You salute. A passing officer walks directly through where your hand should be, somehow. Dignity -1.",
    "Beautiful salute. Held it for a full count. The only witness was a coolant fly.",
]


def cmd_salute(world, command, session) -> HandlerResult:
    world.flags["dignity_lost"] = world.flags.get("dignity_lost", 0) + 1
    return HandlerResult(text=choice(SALUTE_REPLIES))


FRAK_LAMENTS = [
    "\"Frak,\" you mutter. It helps. A little.",
    "\"FRAK,\" you announce to the room. Nobody disagrees.",
    "You exhale. \"Frak me sideways.\" The ship hums in solidarity.",
    "\"Frak,\" you say. Then again. Then a third time, for the gods.",
    "You make eye contact with the middle distance. \"Frak.\"",
    "\"Frak this entire frakkin' ship,\" you whisper. The ship pretends not to hear.",
    "\"Frak,\" you say, with feeling. A coolant pipe sighs in agreement.",
    "You consider, briefly, every life choice that led to this moment. \"Frak.\"",
    "\"Oh for frak's SAKE,\" you tell the ceiling. The ceiling does not respond. The ceiling never responds.",
    "\"Frak.\" You let it sit. You let it BREATHE. You move on.",
    "You picture a beach. You picture cold beer. You picture not being here. \"Frak.\"",
    "\"You know what? Frak.\" You don't elaborate. The bulkhead understands.",
    "\"Frakkin' frak,\" you say, which is grammatically interesting and emotionally accurate.",
    "You make a small noise. It is the noise of a man whose mop has bested him. \"Frak.\"",
    "\"Frak this. Frak that. Frak THIS frakkin' ship,\" you whisper-shout into your collar.",
    "You imagine the Cylons just getting it over with. \"Frak.\"",
    "\"Frak,\" you say, the way the gods must have said it on day six.",
    "You take a long breath. You let it out. \"Frak.\"",
    "\"FRAK,\" you say. A passing officer mistakes it for an order and salutes a wall.",
    "You count to ten. You get to four. \"Frak.\"",
    "\"Frak,\" you say, in the tone of someone who has been saying \"frak\" since basic.",
    "You wonder if it's still considered an interjection if it's a lifestyle. \"Frak.\"",
    "\"Frak me, frak you, frak them, frak it,\" you conjugate quietly, like a meditation.",
    "You look up at the lights. The lights flicker, in solidarity, or possibly because of a power surge. \"Frak.\"",
    "\"FRAK,\" you bellow, just to hear it echo. It does not echo. The acoustics down here are a war crime.",
]


def cmd_frak(world, command, session) -> HandlerResult:
    # Deterministic rotation so the player sees variety rather than repeats.
    idx = world.flags.get("__frak_index__", 0)
    world.flags["__frak_index__"] = idx + 1
    return HandlerResult(text=FRAK_LAMENTS[idx % len(FRAK_LAMENTS)])


def cmd_drink(world, command, session) -> HandlerResult:
    if not command.obj:
        return HandlerResult(text="Drink what, specialist? The recycled air?")
    item = _resolve_in_inventory(command.obj, world) or _resolve_in_room_items(command.obj, world)
    if item is None:
        return HandlerResult(text=f"You don't have any \"{command.obj}\" to drink.")
    if item.on_drink is None:
        return HandlerResult(text=f"You can't drink the {item.name}. Or — well — you could, but you really shouldn't.")
    return HandlerResult(text=item.on_drink(world))


def cmd_eat(world, command, session) -> HandlerResult:
    if not command.obj:
        return HandlerResult(text="Eat what?")
    item = _resolve_in_inventory(command.obj, world) or _resolve_in_room_items(command.obj, world)
    if item is None:
        return HandlerResult(text=f"You don't have any \"{command.obj}\" to eat.")
    if item.on_eat is None:
        return HandlerResult(text=f"That is not food, specialist. You know this.")
    return HandlerResult(text=item.on_eat(world))


# ─── dispatch ──────────────────────────────────────────────────────────────────

HANDLERS: dict[str, Callable] = {
    "look": cmd_look,
    "examine": cmd_examine,
    "go": cmd_go,
    "take": cmd_take,
    "drop": cmd_drop,
    "inventory": cmd_inventory,
    "talk": cmd_talk,
    "use": cmd_use,
    "give": cmd_give,
    "wait": cmd_wait,
    "save": cmd_save,
    "load": cmd_load,
    "help": cmd_help,
    "quit": cmd_quit,
    "salute": cmd_salute,
    "frak": cmd_frak,
    "drink": cmd_drink,
    "eat": cmd_eat,
}


def dispatch(world: WorldState, command: Command, session) -> HandlerResult:
    if command.error == "empty":
        return HandlerResult(text="", advance_turn=False)
    if command.error == "unknown_verb" or command.verb is None:
        return HandlerResult(text=choice(UNKNOWN_VERB_REPLIES), advance_turn=False)
    handler = HANDLERS.get(command.verb)
    if handler is None:
        return HandlerResult(text=choice(UNKNOWN_VERB_REPLIES), advance_turn=False)
    return handler(world, command, session)
