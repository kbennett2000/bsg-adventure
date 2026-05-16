"""Items for the opening slice."""

from engine.models import Item
from engine.registry import register_item
from engine.world import move_item_to_room


# ─── algae bar ─────────────────────────────────────────────────────────────────


def algae_bar_on_eat(world):
    if world.flags.get("algae_bar_eaten"):
        return "You already ate it. There is no more bar. There is only memory."
    world.flags["algae_bar_eaten"] = True
    # Bar is now gone from inventory/room
    if "algae_bar" in world.inventory:
        world.inventory.remove("algae_bar")
    for items in world.room_items.values():
        if "algae_bar" in items:
            items.remove("algae_bar")
    return (
        "You finish the algae bar. It tastes exactly like the inside of a vent — which "
        "is something you happen to be an expert on. Nutritionally adequate. Spiritually, a war crime."
    )


register_item(Item(
    id="algae_bar",
    name="half-eaten algae bar",
    aliases=["algae", "bar", "algae bar", "food"],
    description=(
        "A regulation-issue algae bar. Someone — possibly you, possibly your bunkmate, "
        "possibly a small frightened rat — has taken a bite out of one end. The bite marks "
        "are not enthusiastic."
    ),
    takeable=True,
    on_eat=algae_bar_on_eat,
))


# ─── mop ───────────────────────────────────────────────────────────────────────


def mop_on_use(world):
    return (
        "You give the deck a professional once-over. It looks marginally less haunted. "
        "Somewhere, an officer feels vaguely better about themselves and does not know why."
    )


register_item(Item(
    id="mop",
    name="regulation mop",
    aliases=["mop"],
    description=(
        "Your mop. Standard issue, deck-five environmental. The handle has 'PROPERTY OF "
        "SPECIALIST' carved into it in three different handwritings, none of them yours. "
        "You love this mop."
    ),
    takeable=True,
    on_use=mop_on_use,
))


# ─── dented locker (scenery, not takeable) ────────────────────────────────────


def locker_on_use(world):
    if world.flags.get("opened_locker"):
        return (
            "You open the locker again. The contents are exactly the same as last time, "
            "which is more than you can say for most things on this ship."
        )
    world.flags["opened_locker"] = True
    return (
        "You wrench the locker open. Inside:\n"
        "  - one (1) regulation cap, worn.\n"
        "  - one (1) half-finished letter to your mom you've been working on for nine months.\n"
        "  - one (1) framed picture of a dog named Captain Frakkin' Adorable.\n"
        "  - a small, suspicious nutrient paste packet from 'before the cylons came back'.\n"
        "You close the locker. The contents do not require you right now."
    )


register_item(Item(
    id="locker",
    name="dented locker",
    aliases=["locker"],
    description=(
        "Your locker. Dented in three places: once from a bulkhead collision during the "
        "first Cylon attack, once from when Hadrian fell on it drunk, and once from a "
        "cause you genuinely cannot remember. The dent without a story bothers you the most."
    ),
    takeable=False,
    on_use=locker_on_use,
))


# ─── blinking console ─────────────────────────────────────────────────────────


def console_on_use(world):
    world.flags["noticed_anomaly"] = True
    return (
        "You tap a key. The screen scrolls:\n\n"
        "    COOLANT FLOW: NOMINAL\n"
        "    COOLANT FLOW: NOMINAL\n"
        "    COOLANT FLOW: ANOMALY DETECTED — DECK 9 VALVE 7B\n"
        "    COOLANT FLOW: NOMINAL\n"
        "    COOLANT FLOW: NOMINAL\n\n"
        "Huh. Deck 9 Valve 7B. You make a mental note to investigate. You will absolutely "
        "forget about this by lunch."
    )


register_item(Item(
    id="console",
    name="environmental console",
    aliases=["console", "screen", "terminal", "computer"],
    description=(
        "An environmental control console. One light blinks insistently. The others have "
        "given up. The keyboard is missing the 'F' key, which is fine because you can spell "
        "'frak' with what's left."
    ),
    takeable=False,
    on_use=console_on_use,
))


# ─── bunk ─────────────────────────────────────────────────────────────────────


register_item(Item(
    id="bunk",
    name="your bunk",
    aliases=["bunk", "bed", "rack"],
    description=(
        "Your rack. Bottom of a three-high stack. The springs make a noise that you have "
        "had to describe to medical professionals more than once. The mattress is a hate "
        "crime."
    ),
    takeable=False,
))


# ─── canteen (given by Tigh) ──────────────────────────────────────────────────


def canteen_on_drink(world):
    if world.flags.get("canteen_filled"):
        return (
            "You unscrew the cap. The fumes alone make your eyes water and your career "
            "flash before them. You screw the cap back on. The XO would frakkin' space you."
        )
    return (
        "You unscrew the cap and tilt it back. It's empty. Of course it's empty. You're "
        "supposed to fill it."
    )


def canteen_on_use(world):
    return (
        "It's a canteen. Right now it's empty. The XO seemed to think that was a problem "
        "to be solved in Engineering."
    )


register_item(Item(
    id="canteen",
    name="battered canteen",
    aliases=["canteen", "flask", "bottle"],
    description=(
        "A dented metal canteen, military issue, with the XO's name scratched off and "
        "replaced with 'WATER ONLY' in three different sets of handwriting. It is empty. "
        "It smells like a regrettable decision."
    ),
    takeable=True,
    on_drink=canteen_on_drink,
    on_use=canteen_on_use,
))


# ─── the napkin (the spine of the entire game) ────────────────────────────────


def _has_jump_context(world) -> bool:
    """True once the player has accumulated enough context to recognize the napkin's
    numbers as FTL jump coordinates rather than a phone number or recipe."""
    flags = world.flags
    score = 0
    if flags.get("heard_adama_jump_prep"):
        score += 1
    if flags.get("heard_roslin_prophecy"):
        score += 1
    if flags.get("heard_hadrian_jump_gossip"):
        score += 1
    if flags.get("heard_intercom_jump_prep"):
        score += 1
    return score >= 1  # any one source is enough


def napkin_on_examine_text(world) -> str:
    """The napkin's description morphs as the player accumulates context."""
    if world.flags.get("realized_napkin_is_coords"):
        return (
            "The napkin. You can no longer un-see it. Those numbers are FTL jump "
            "coordinates. The XO must have been working them out in here — between "
            "sips, between hums, between whatever it is he does in stalls — and then "
            "dropped them. The fleet's next jump. ON A FRAKKIN' NAPKIN."
        )
    if _has_jump_context(world):
        # Trigger realization on this examine.
        world.flags["realized_napkin_is_coords"] = True
        return (
            "A used napkin, military-grade, suspiciously absorbent. Numbers in shaky "
            "handwriting: seven groups of digits, separated by dashes. You stare at it. "
            "You stare at it some more.\n\n"
            "Wait.\n\n"
            "Wait.\n\n"
            "That's not a phone number. That's not a recipe. Those are FTL coordinates. "
            "That's the FORMAT. Seven-group, dash-separated, that's the frakkin' jump "
            "vector format from your basic training. The XO was working out the fleet's "
            "NEXT JUMP. In a TOILET STALL. On a NAPKIN. And he DROPPED IT.\n\n"
            "You look around the room. The room does not help."
        )
    return (
        "A used napkin. It has been crumpled, smoothed, crumpled again. There are "
        "numbers on it in shaky handwriting: seven groups of digits, separated by "
        "dashes. Probably a phone number. Probably a recipe. Probably nothing. "
        "Probably."
    )


register_item(Item(
    id="napkin",
    name="crumpled napkin",
    aliases=["napkin", "paper", "scrap", "numbers"],
    description="A crumpled napkin with numbers on it.",  # overridden by on_examine when examined
    takeable=True,
))


# Patch examine to be dynamic — we'll resolve it in commands.cmd_examine via a callback.
# Simpler approach: override description via a runtime check in the examine handler.
# We do that by attaching the dynamic text function as an attribute the handler checks.
ITEMS_NAPKIN = None  # placeholder; resolved at import time below


def _attach_dynamic_napkin():
    from engine.registry import ITEMS as _ITEMS
    _ITEMS["napkin"].description = "<dynamic>"  # marker — see commands.cmd_examine
    _ITEMS["napkin"]._dynamic_description = napkin_on_examine_text  # type: ignore[attr-defined]


_attach_dynamic_napkin()

