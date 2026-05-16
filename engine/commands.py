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
    advance_shift,
    bump_stat,
    get_stat,
    items_in_room,
    move_item_to_inventory,
    move_item_to_room,
    set_stat,
    shift_name,
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


_SUBSTRING_MIN_LEN = 3   # below this, queries must be exact name or alias matches


def _matches(query: str, thing) -> bool:
    q = query.lower().strip()
    name = thing.name.lower()
    aliases = [a.lower() for a in getattr(thing, "aliases", [])]
    # Exact name or alias always wins. This is what short canonical names
    # like "six", "tigh", "mop" hit; the substring path below would also
    # have caught them, but exact match is more correct AND lets us gate
    # substring on a minimum length.
    if q == name or q in aliases:
        return True
    # Substring matches are too eager for very short queries — `examine c`
    # used to match "ceiling", "console", "cigarette", etc. depending on
    # resolve order. Require at least 3 chars to fall back to substring.
    if len(q) < _SUBSTRING_MIN_LEN:
        return False
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


def _npcs_present(world: WorldState, room_id: str) -> list[str]:
    """Compute which NPCs are present in `room_id` at the current watch.
    Schedules take precedence: an NPC with a schedule entry only appears in
    rooms it is scheduled to be in. NPCs without schedules use their static
    room.npcs placement (legacy behavior). NPCs flagged 'dead' (via the
    Cylon-resurrection world-drift) are filtered out entirely."""
    try:
        from content.schedules import SCHEDULES, npcs_scheduled_for
    except Exception:
        return [n for n in ROOMS[room_id].npcs if _npc_visible(world, n)
                and not world.flags.get(f"npc_dead_{n}")]
    static_npcs = ROOMS[room_id].npcs
    present: list[str] = []
    for npc_id in npcs_scheduled_for(room_id, world.shift):
        if world.flags.get(f"npc_dead_{npc_id}"):
            continue
        if _npc_visible(world, npc_id) and npc_id not in present:
            present.append(npc_id)
    for npc_id in static_npcs:
        if npc_id in SCHEDULES:
            continue
        if world.flags.get(f"npc_dead_{npc_id}"):
            continue
        if _npc_visible(world, npc_id) and npc_id not in present:
            present.append(npc_id)
    return present


def _resolve_npc(query: str, world: WorldState) -> Optional[NPC]:
    for npc_id in _npcs_present(world, world.current_room):
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
    body = _apply_stat_filter(body, world)
    parts = [f"── {room.name.upper()} ──", "", body]
    room_items = items_in_room(world, room.id)
    if room_items:
        names = [ITEMS[i].name for i in room_items]
        parts += ["", "You see: " + ", ".join(names) + "."]
    present_ids = _npcs_present(world, room.id)
    visible_npc_names = [NPCS[n].name for n in present_ids]
    # Exhaustion ≥ 80: hallucinate a phantom in the room
    if get_stat(world, "exhaustion") >= 80:
        phantom = _exhaustion_phantom(world)
        if phantom:
            visible_npc_names.append(phantom)
    if visible_npc_names:
        parts += ["", "Present: " + ", ".join(visible_npc_names) + "."]
    visible_exit_set = set(room.exits.keys())
    for direction, (_target, cond) in room.hidden_exits.items():
        try:
            if cond(world):
                visible_exit_set.add(direction)
        except Exception:
            pass
    if visible_exit_set:
        parts += ["", "Exits: " + ", ".join(sorted(visible_exit_set)) + "."]
    return "\n".join(parts)


def _apply_stat_filter(text: str, world: WorldState) -> str:
    """Append loopy / cylon-creepy / paranoid commentary to a description body
    based on the player's current stat levels. Never reveal raw numbers."""
    suffixes = []
    ex = get_stat(world, "exhaustion")
    sus = get_stat(world, "suspicion")
    cv = get_stat(world, "cylon_vibes")
    if ex >= 80:
        suffixes.append(
            " The edges of everything are doing a thing. The thing is bad. You "
            "should sit down. You should have sat down two corridors ago."
        )
    elif ex >= 50:
        suffixes.append(
            " You blink. You blink again. The room is the room. The room is still "
            "the room. You're pretty sure."
        )
    if sus >= 75:
        suffixes.append(
            " You feel watched. There is a non-zero chance you ARE watched."
        )
    if cv >= 60:
        suffixes.append(
            " There's a song stuck in your head that you don't remember learning. "
            "You hum a bar of it. It does not stop."
        )
    return text + "".join(suffixes)


_PHANTOMS = [
    "someone who looks like Hadrian but with the wrong number of fingers",
    "a deckhand standing very still and facing the corner",
    "yourself, except shorter",
    "a Six in red, peripherally, when you turn she's gone",
    "an officer you can't quite place, smiling without teeth",
]


def _exhaustion_phantom(world: WorldState) -> str | None:
    """Pick a phantom NPC based on turn count for determinism (so saves replay sanely)."""
    if get_stat(world, "exhaustion") < 80:
        return None
    return _PHANTOMS[world.turn % len(_PHANTOMS)]


def _npc_visible(world: WorldState, npc_id: str) -> bool:
    """NPCs can be conditionally hidden via flags (e.g., 'npc_hidden_six')."""
    return not world.flags.get(f"npc_hidden_{npc_id}", False)




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
    new_id = None
    if direction in room.exits:
        new_id = room.exits[direction]
    elif direction in room.hidden_exits:
        target, cond = room.hidden_exits[direction]
        try:
            available = cond(world)
        except Exception:
            available = False
        if available:
            new_id = target
    if new_id is None:
        return HandlerResult(text=f"There's no way {direction} from here. The bulkhead disagrees with you.", advance_turn=False)
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
    # Optional take-guard: content can attach `_take_guard(world)` returning a string to deny pickup.
    guard = getattr(item, "_take_guard", None)
    if callable(guard):
        denial = guard(world)
        if denial:
            return HandlerResult(text=denial)
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
        # `use X on Y` — dispatch through the item's on_use_with table if it
        # has a registered handler for this specific target. Resolve the target
        # against everything in scope (room items, NPCs, or inventory).
        target_thing = _resolve_any(command.target, world)
        if target_thing is None:
            return HandlerResult(
                text=f"You don't see any \"{command.target}\" to use the {item.name} on."
            )
        handler = item.on_use_with.get(target_thing.id) if item.on_use_with else None
        if handler is None:
            return HandlerResult(
                text=f"You wave the {item.name} vaguely at the {target_thing.name}. "
                     "Nothing happens. You feel watched."
            )
        result = handler(world)
        if isinstance(result, HandlerResult):
            return result
        return HandlerResult(text=result)
    if item.on_use is None:
        return HandlerResult(text=f"You can't think of anything productive to do with the {item.name} right now.")
    result = item.on_use(world)
    if isinstance(result, HandlerResult):
        return result
    return HandlerResult(text=result)


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
    # Laying low: a small suspicion-reducer. Cap at 0 via bump_stat clamping.
    bump_stat(world, "suspicion", -1)
    return HandlerResult(text="You stand there. Time advances. The ship hums. Somewhere, an officer sighs meaningfully.")


def cmd_sleep(world, command, session) -> HandlerResult:
    """Sleep through one watch. Exhaustion to zero, time advances by one shift.
    Skipping your assigned duty by sleeping is the player's problem — the
    duty roster will not, on balance, be sympathetic."""
    set_stat(world, "exhaustion", 0)
    bump_stat(world, "morale", 2)
    advance_shift(world, 1)
    # advance_shift already reset turns_this_shift. Trigger the shift-change
    # hooks (banner, duty rollover, hunger) via the session's normal path.
    text = (
        "You climb into your rack. The mattress is, as ever, a hate crime.\n"
        "You close your eyes. You open them. You are, briefly, unsure how long\n"
        "you slept. The fluorescents say 'a while.' The fluorescents are lying."
    )
    # Manually fire the shift-change banner since this didn't go through the
    # auto-tick path that normally handles it.
    if session is not None:
        try:
            session._on_shift_change()  # type: ignore[attr-defined]
        except AttributeError:
            pass
    return HandlerResult(text=text, advance_turn=False)


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
    # Copy every WorldState field from the loaded snapshot. Note: any new
    # field added to WorldState MUST be listed here or it will silently fail
    # to restore on load. The full-state-save sentinel test exists to catch
    # exactly this mistake.
    for attr in (
        "player_name", "current_room", "inventory", "room_items",
        "flags", "turn", "npc_state", "visited_rooms", "stats",
        "shift", "day", "turns_this_shift",
    ):
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
        "  wait                       — let a turn pass; lower your profile (suspicion -1)\n"
        "  sleep                      — sleep through one watch. Exhaustion to 0. Time advances.\n"
        "  save [slot] / load [slot]  — save your game / load it back\n"
        "  status                     — how you're feeling, what your uniform's doing\n"
        "  hint                       — Adama, in your head, says something cryptic but useful\n"
        "  salute                     — render proper respect (or don't)\n"
        "  frak                       — express yourself. Burns a turn.\n"
        "  quit                       — leave the ship\n"
    )
    return HandlerResult(text=text, advance_turn=False)


def cmd_quit(world, command, session) -> HandlerResult:
    return HandlerResult(text="Frak out, specialist.", quit=True, advance_turn=False)


# ─── status (the player's vibe check) ──────────────────────────────────────────

# Each entry: (predicate(stats_dict) → bool, vibe_line).
# Evaluated in order; the FIRST match wins. Most extreme conditions go first.

def _vibe_line(stats: dict[str, int]) -> str:
    m, s, c, e = stats["morale"], stats["suspicion"], stats["cylon_vibes"], stats["exhaustion"]
    # Crisis-level vibes
    if s >= 90:
        return "You feel like Tigh's been watching you. He has."
    if e >= 90:
        return "You feel like a wet uniform with a person in it."
    if c >= 80:
        return "All Along the Watchtower is stuck in your head. You don't remember ever hearing it."
    # Severe
    if s >= 75:
        return "You feel like every officer you pass is filing a report about your face."
    if c >= 60:
        return "There's a hum behind your thoughts. It is not the ship. The ship doesn't hum in B-flat."
    if e >= 70:
        return "You feel like you slept on the floor in someone else's body."
    if m <= 15:
        return "You feel hollow in a way no algae bar can fix."
    # Moderate
    if m >= 80 and e < 30 and s < 30:
        return "You feel frakking unstoppable."
    if m >= 70 and c >= 30:
        return "You feel weirdly into this. Whatever this is."
    if s >= 40:
        return "You feel like the wrong people know your name."
    if c >= 30:
        return "You feel observed in a way that isn't entirely uncomfortable."
    if e >= 40:
        return "You feel like you've been on shift for nine days. You haven't. You think."
    if m <= 30:
        return "You feel the specific weight of a mop you have not yet picked up."
    # Default — mid-range on everything
    return "You feel fine. Considering. The ship is still attached. You are still attached to the ship."


def _uniform_state(stats: dict[str, int]) -> str:
    e = stats["exhaustion"]
    m = stats["morale"]
    if e >= 80:
        return "Your uniform has surrendered."
    if e >= 50:
        return "Your uniform smells like coolant, ambrosia, and giving up."
    if m >= 70:
        return "Your uniform is regulation enough. Probably."
    if m <= 25:
        return "Your uniform looks like it's been on shift longer than you have."
    return "Your uniform is fine. You think. You haven't looked."


def _body_verb(stats: dict[str, int]) -> str:
    e = stats["exhaustion"]
    if e >= 80:
        return "You stand by leaning on something."
    if e >= 50:
        return "You shift your weight. Both feet are tired. Pick one."
    if e >= 25:
        return "You roll your shoulders. They roll back."
    return "You stand up straight. You sit down. You stand up straight again. You are fine."


def cmd_status(world, command, session) -> HandlerResult:
    # Force stat init for back-compat saves
    from .world import _ensure_stats
    _ensure_stats(world)
    stats = world.stats
    vibe = _vibe_line(stats)
    uniform = _uniform_state(stats)
    body = _body_verb(stats)
    clock = f"It is {shift_name(world)}, day {world.day}."
    text = "\n".join([vibe, uniform, body, clock])
    return HandlerResult(text=text, advance_turn=False)


# ─── hint — Adama-style cryptic guidance based on quest flags ─────────────────

def _hint_line(world) -> str:
    """Compute a cryptic-but-useful nudge based on current quest state. The
    point: a confused player can always advance the game. Adama-flavored:
    sounds profound, is actually a specific instruction if you decode it."""
    f = world.flags
    inv = world.inventory

    # Active press conference takes priority — the player has no normal verbs
    # right now and may not know it.
    if f.get("press_active"):
        return (
            "Adama, in your head, says: 'A man at a podium chooses a path. There\n"
            "are three paths. None of them is the right path. Pick one anyway.'\n"
            "(Type: honest, political, or unhinged.)"
        )

    if f.get("__ended__"):
        return (
            "Some shifts end. The shift ended. You can begin again, or you can\n"
            "leave. Either is a kind of beginning."
        )

    # Has the player even started the main quest?
    if not f.get("got_canteen"):
        return (
            "Adama, in your head, says: 'A man cannot mop forever, son. Sometimes\n"
            "a man must walk EAST. To a room with a closed door. To a man with a\n"
            "thirst.' He is, somehow, correct."
        )

    # Got canteen; have they found the napkin yet?
    if "napkin" not in inv and "napkin" not in world.room_items.get("head_deck_5", []):
        return (
            "Adama, in your head, says: 'A man finds a napkin where a man drops a\n"
            "napkin. Floors are not, son, just floors. They are testimony.'\n"
            "(Try the floor. Or the tile. Or the stall. You'll know it when you\n"
            "see it.)"
        )

    # Napkin in room but not picked up yet
    if "napkin" in world.room_items.get("head_deck_5", []):
        return (
            "Adama, in your head, says: 'A specialist who SEES is half a specialist.\n"
            "A specialist who TAKES is a frakkin' man.' Take the thing, son."
        )

    # Player has napkin, hasn't realized
    if "napkin" in inv and not f.get("realized_napkin_is_coords"):
        return (
            "Adama, in your head, says: 'Numbers are mirrors, son. You see in them\n"
            "what you have lived. You have not, yet, lived a jump. Listen to those\n"
            "who have.'\n"
            "(Find someone who can tell you what these numbers ARE. The mess hall\n"
            "specialists. The bridge. Roslin, in sickbay.)"
        )

    # Realized but hasn't reached CIC
    if f.get("realized_napkin_is_coords") and world.current_room != "cic":
        return (
            "Adama, in your head, says: 'The paper goes to the man at the plot.\n"
            "The man at the plot is, son, north. North of north. Through the\n"
            "carpet.'\n"
            "(Get to CIC. Up from corridor B-7, then north from corridor A.)"
        )

    # In CIC with napkin
    if world.current_room == "cic" and "napkin" in inv:
        return (
            "Adama, in your head, says: 'Give a man what is HIS, son. Not a word.\n"
            "Not a salute. The THING. The thing in your hand.'\n"
            "(Try: give napkin to adama.)"
        )

    return (
        "Adama, in your head, says: 'The frakkin' tide of duty is constant, son.\n"
        "When in doubt, do something. When that fails, do something ELSE.'\n"
        "(Wander a corridor. Talk to a specialist. Examine a thing. Mop a deck.\n"
        "Examine the duty roster in Corridor C-12. Eat in the mess at Morning\n"
        "or Afternoon. Sleep if you're tired. Wait if you're paranoid.)"
    )


def cmd_hint(world, command, session) -> HandlerResult:
    return HandlerResult(text=_hint_line(world), advance_turn=False)


# ─── flavor verbs ──────────────────────────────────────────────────────────────

SALUTE_REPLIES = [
    "You snap to. Nobody salutes back. Nobody looks. Your hand returns to its post in shame.",
    "Crisp. Textbook. The bulkhead does not return your salute. Dignity -1.",
    "You salute. A passing officer walks directly through where your hand should be, somehow. Dignity -1.",
    "Beautiful salute. Held it for a full count. The only witness was a coolant fly.",
]


def cmd_salute(world, command, session) -> HandlerResult:
    world.flags["dignity_lost"] = world.flags.get("dignity_lost", 0) + 1
    bump_stat(world, "morale", -3)
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
    bump_stat(world, "morale", 1)  # catharsis (small — each frak also costs a turn)
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
    "sleep": cmd_sleep,
    "save": cmd_save,
    "load": cmd_load,
    "help": cmd_help,
    "quit": cmd_quit,
    "salute": cmd_salute,
    "frak": cmd_frak,
    "drink": cmd_drink,
    "eat": cmd_eat,
    "status": cmd_status,
    "hint": cmd_hint,
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
