"""Items for the opening slice."""

from engine.models import Item
from engine.registry import register_item
from engine.world import bump_stat, move_item_to_room


# ─── algae bar ─────────────────────────────────────────────────────────────────


def algae_bar_on_eat(world):
    if world.flags.get("algae_bar_eaten"):
        return "You already ate it. There is no more bar. There is only memory."
    world.flags["algae_bar_eaten"] = True
    if "algae_bar" in world.inventory:
        world.inventory.remove("algae_bar")
    for items in world.room_items.values():
        if "algae_bar" in items:
            items.remove("algae_bar")
    bump_stat(world, "morale", -2)         # algae is depressing
    bump_stat(world, "exhaustion", -3)     # but it IS nourishment
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
    bump_stat(world, "morale", -3)         # actual work tanks morale
    bump_stat(world, "exhaustion", 4)       # and it's tiring
    bump_stat(world, "suspicion", -1)       # but you look like you're doing your job
    base = (
        "You give the deck a professional once-over. It looks marginally less haunted. "
        "Somewhere, an officer feels vaguely better about themselves and does not know why."
    )
    # If today's duty is to mop the head AND we're currently in the head,
    # this fulfills it. The duty hook handles morale/suspicion separately.
    if world.current_room == "head_deck_5":
        try:
            from content.duties import on_mop_head
            extra = on_mop_head(world)
            if extra:
                return base + "\n\n" + extra
        except Exception:
            pass
    return base


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
    # Looking at the dent without a story bumps cylon-vibes (deja vu).
    bump_stat(world, "cylon_vibes", 2)
    return (
        "You wrench the locker open. Inside:\n"
        "  - one (1) regulation cap, worn.\n"
        "  - one (1) half-finished letter to your mom you've been working on for nine months.\n"
        "  - one (1) framed picture of a dog named Captain Frakkin' Adorable.\n"
        "  - a small, suspicious nutrient paste packet from 'before the cylons came back'.\n"
        "You close the locker. The third dent in the door — the one without a story — "
        "looks somehow familiar in a way it shouldn't. You move on."
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
    bump_stat(world, "morale", -2)          # doing your actual job
    bump_stat(world, "exhaustion", 2)
    base = (
        "You tap a key. The screen scrolls:\n\n"
        "    COOLANT FLOW: NOMINAL\n"
        "    COOLANT FLOW: NOMINAL\n"
        "    COOLANT FLOW: ANOMALY DETECTED — DECK 9 VALVE 7B\n"
        "    COOLANT FLOW: NOMINAL\n"
        "    COOLANT FLOW: NOMINAL\n\n"
        "Huh. Deck 9 Valve 7B. You make a mental note to investigate. You will absolutely "
        "forget about this by lunch."
    )
    try:
        from content.duties import on_reroute_coolant
        extra = on_reroute_coolant(world)
        if extra:
            return base + "\n\n" + extra
    except Exception:
        pass
    return base


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
        bump_stat(world, "morale", 5)
        bump_stat(world, "suspicion", 8)    # drinking the XO's stash on duty
        bump_stat(world, "exhaustion", -5)
        world.flags["tigh_drink_count"] = world.flags.get("tigh_drink_count", 0) + 1
        return (
            "You unscrew the cap. The fumes alone make your eyes water and your career "
            "flash before them. You take a sip anyway, because you have made it this "
            "far on bad choices and you are not about to stop now. It burns. It also, "
            "weirdly, helps."
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
    aliases=["canteen"],   # NB: "flask" used to be aliased here but now collides
                            # with the actual flask item (stash quest bottle #1).
                            # "bottle" is too generic and shared with stash bottles.
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


# ─── cigarette (Doc Cottle's contraband) ──────────────────────────────────────


def cigarette_on_use(world):
    if world.flags.get("cigarette_smoked"):
        return (
            "It's already smoked, specialist. There's no cigarette. There's only the\n"
            "lingering smell of regulation tobacco and questionable medical advice."
        )
    world.flags["cigarette_smoked"] = True
    if "cigarette" in world.inventory:
        world.inventory.remove("cigarette")
    bump_stat(world, "morale", 6)
    bump_stat(world, "exhaustion", 4)
    return (
        "You light it. You inhale. It is genuinely terrible. It is also genuinely\n"
        "great. The world becomes, for one moment, exactly the manageable size it\n"
        "should always have been. You exhale a long blue line. Somewhere, Cottle is\n"
        "smiling. He has not smiled in eight years, so he will not know to attribute\n"
        "it to you."
    )


def cigarette_on_eat(world):
    return "Don't eat the frakkin' cigarette, specialist."


def cigarette_on_drink(world):
    return "It is not a beverage. Cottle would yell at both of us."


# ─── Mess hall tray (handles the hunger mechanic) ─────────────────────────────


def _tray_on_eat(world):
    # Dispatch to the mess-hall handler in rooms.py — it knows whether the
    # mess is currently open and whether the player has already eaten today.
    from content.rooms import _mess_eat
    return _mess_eat(world)


register_item(Item(
    id="tray",
    name="regulation lunch tray",
    aliases=["tray", "lasagna", "lunch", "protein", "food", "meal"],
    description=(
        "A regulation lunch tray. Three compartments. All grey. The grey is "
        "structural. You can eat it (eat tray) during Morning Watch or Afternoon "
        "when the mess is actually open."
    ),
    takeable=False,
    on_eat=_tray_on_eat,
))


register_item(Item(
    id="cigarette",
    name="slightly-bent cigarette",
    aliases=["cigarette", "smoke", "cig"],
    description=(
        "A regulation cigarette from Doctor Cottle's private supply. Slightly bent. "
        "Smells like the inside of a fire suppression panel after an incident. The "
        "filter is, in defiance of all known regulations, a fingertip-sized scrap of "
        "paper from a religious tract."
    ),
    takeable=True,
    on_use=cigarette_on_use,
    on_eat=cigarette_on_eat,
    on_drink=cigarette_on_drink,
))


# ─── Presidential commendation letter (press conference reward) ──────────────


def _commendation_on_examine(world):
    return (
        "A folded sheet of presidential letterhead. The handwriting is President\n"
        "Roslin's. Your name is on it. Your name is, you note, misspelled. By two\n"
        "letters. In a way that suggests she heard the name approximately and\n"
        "almost used the wrong one in time.\n\n"
        "The letter commends you for 'extraordinary composure under press scrutiny'\n"
        "and 'a number of remarks of substantial historical interest.' It is\n"
        "signed L.R., and the signature is, you note, slightly damp."
    )


def _commendation_on_use(world):
    if world.flags.get("commendation_used"):
        return "Already used. The letter is creased now. The crease was you."
    world.flags["commendation_used"] = True
    bump_stat(world, "morale", 5)
    bump_stat(world, "suspicion", -10)
    return (
        "You produce the letter at the next checkpoint. The MP reads it. The MP\n"
        "reads it again. The MP looks at you. The MP looks at the misspelled name.\n"
        "The MP shrugs and waves you through.\n\n"
        "It works. It actually works."
    )


register_item(Item(
    id="commendation_letter",
    name="presidential commendation letter",
    aliases=["commendation", "letter", "presidential letter", "press pass"],
    description="<dynamic>",
    takeable=True,
    on_use=_commendation_on_use,
))


def _attach_commendation_dynamic():
    from engine.registry import ITEMS as _ITEMS
    _ITEMS["commendation_letter"]._dynamic_description = _commendation_on_examine  # type: ignore[attr-defined]


_attach_commendation_dynamic()


# ─── Tigh's flask (stash quest bottle #1) ──────────────────────────────────────

def _stash_swig(world):
    """Shared swig handler for any of the three stash bottles. The reward swig:
    +morale, +exhaustion, marginally suspicious. Counts toward the Lahey-coded
    achievement (drinking with Tigh, broadly construed)."""
    bump_stat(world, "morale", 6)
    bump_stat(world, "exhaustion", 6)
    bump_stat(world, "suspicion", 2)
    world.flags["tigh_drink_count"] = world.flags.get("tigh_drink_count", 0) + 1
    return (
        "You unscrew the cap. It hisses. You take a sip. It is — gods. It is.\n\n"
        "Your eyes water. Your throat learns something new about itself. The\n"
        "world becomes briefly, vividly, exactly the size of your own face. You\n"
        "are awake in a different way than before. You are also tired in a\n"
        "different way than before. Both are improvements. Maybe."
    )


register_item(Item(
    id="flask",
    name="Tigh's hip flask",
    aliases=["flask", "hip flask", "bottle"],
    description=(
        "A battered hip flask, monogrammed S.T. The S is more battered than the T. "
        "Heavier than it ought to be. Smells like a fire that learned how to feel."
    ),
    takeable=True,
    on_drink=_stash_swig,
))


# ─── Stash bottle #2 (mess hall) ──────────────────────────────────────────────

register_item(Item(
    id="stash_bottle_mess",
    name="suspicious thermos",
    aliases=["thermos", "stash thermos", "bottle"],
    description=(
        "A regulation-issue thermos with COFFEE — DO NOT DRINK — TIGH written on "
        "it in three different markers and one (1) clear act of forgery. It is "
        "not coffee. The thermos has been very specifically labelled to be unappealing."
    ),
    takeable=True,
    on_drink=_stash_swig,
))


# ─── Stash bottle #3 (hangar deck) ────────────────────────────────────────────

register_item(Item(
    id="stash_bottle_hangar",
    name="grease-can bottle",
    aliases=["grease can", "grease bottle", "can", "bottle"],
    description=(
        "An empty deck-issue grease can with a screwtop. The grease can is\n"
        "deeply unconvincing, mostly because it is full of liquid that sloshes\n"
        "wrong. It also smells like a fire that learned how to feel."
    ),
    takeable=True,
    on_drink=_stash_swig,
))


# ─── Photo of Adama and Tigh from the academy ─────────────────────────────────

def photo_on_examine(world):
    if not world.flags.get("examined_academy_photo"):
        world.flags["examined_academy_photo"] = True
        bump_stat(world, "suspicion", 20)
        return (
            "A black-and-white photo. The Adama Academy, decades ago. Two young\n"
            "officers in dress uniform. One is recognizably Bill Adama, hair black,\n"
            "smile unfamiliar. The other is recognizably Saul Tigh, both eyes\n"
            "intact, much thinner, holding Bill's hand below the frame in a way\n"
            "that the photographer almost certainly did not stage and absolutely\n"
            "definitely captured.\n\n"
            "On the back, in tight pencil handwriting: 'Saul + Bill — Picon, last\n"
            "shore leave before the assignment. Don't lose this.'\n\n"
            "You stare at it. You stare at it some more. You will be unable, for the\n"
            "rest of your life, to un-see it. You will be unable, for the rest of\n"
            "your shorter life, to forget that you saw it."
        )
    return (
        "The same photograph. The same hands. The same below-frame thing. The same\n"
        "implication. The same career-ending implication. You put it back. You always\n"
        "put it back."
    )


register_item(Item(
    id="photo_academy",
    name="academy photograph",
    aliases=["photo", "photograph", "picture"],
    description="<dynamic>",
    takeable=True,
))


# ─── Cylon detector prototype ────────────────────────────────────────────────

def cylon_detector_on_use(world):
    """Beeps at a random NPC in the room, or occasionally at the player.

    Hidden mechanic: if the player has crossed the silent Cylon threshold,
    the detector beeps at THEM every time. Deterministic, not random."""
    import random
    from engine.registry import NPCS, ROOMS

    # Cylon path: deterministic, always points at player.
    if world.flags.get("is_cylon"):
        bump_stat(world, "cylon_vibes", 5)
        bump_stat(world, "morale", -3)
        return (
            "The detector hums. The detector beeps. The needle, this time, does\n"
            "not waver. It points at you. It has, you suspect, always pointed at\n"
            "you. You hold it at arm's length. The needle follows. You hold it\n"
            "behind your back. The needle, somehow, still follows."
        )

    room = ROOMS[world.current_room]
    candidates = []
    for npc_id in room.npcs:
        candidates.append(("npc", npc_id))
    # ~30% chance the detector points at the player (non-Cylon mode)
    candidates.append(("player", None))
    candidates.append(("player", None))
    if not candidates:
        return "The detector hums. Then it beeps once, sadly, at a fire extinguisher."
    choice = random.choice(candidates)
    if choice[0] == "player":
        bump_stat(world, "cylon_vibes", 10)
        bump_stat(world, "morale", -5)
        return (
            "The detector hums. Then it beeps. Loud. Insistent. Pointed.\n\n"
            "At you.\n\n"
            "It is pointing at YOU, specialist. The needle is hard over. It is\n"
            "humming a chord. You hold the detector at arm's length. The detector\n"
            "follows you, somehow. Baltar made this thing. Baltar made this thing\n"
            "and it works exactly the wrong amount."
        )
    npc = NPCS[choice[1]]
    return (
        f"The detector hums. Then it beeps, very deliberately, at {npc.name}.\n"
        f"{npc.name} does not react. {npc.name} may not have noticed. {npc.name}\n"
        f"may have noticed and decided that reacting was, on balance, a worse outcome\n"
        f"than not reacting. You will not know. You will never know."
    )


register_item(Item(
    id="cylon_detector",
    name="Cylon-detector prototype",
    aliases=["detector", "cylon detector", "prototype", "device"],
    description=(
        "A box with a needle and a hum and three blinking lights. It has Baltar's "
        "handwriting on the side, which is in itself a warning. The device is, "
        "according to its inventor, the only Cylon-detection technology in the "
        "fleet. According to absolutely everyone else, it beeps at fire "
        "extinguishers and cats."
    ),
    takeable=True,
    on_use=cylon_detector_on_use,
))


# ─── Triad cards ─────────────────────────────────────────────────────────────

register_item(Item(
    id="triad_cards",
    name="deck of triad cards",
    aliases=["cards", "deck", "triad cards", "triad"],
    description=(
        "A well-loved deck of triad cards. The corners are folded in ways that, in\n"
        "Starbuck's hands, would not be considered cheating. In yours, would. The\n"
        "back of every card has a slightly different scuff. You have read about\n"
        "this. You have read about this in a book Starbuck almost certainly wrote."
    ),
    takeable=True,
))


# ─── Sealed envelope (CIC — opening it is an ending) ────────────────────────

def sealed_envelope_on_use(world):
    from engine.commands import trigger_ending
    return trigger_ending(
        world,
        "forbidden_knowledge",
        "You break the seal. You hold the envelope by both corners like you're\n"
        "defusing a bomb. You unfold the single sheet of paper inside.\n\n"
        "It is in Adama's handwriting. Clean, deliberate, slightly slanted from\n"
        "years of writing at sea. It says:\n\n"
        "    Saul —\n"
        "    Tuesday. 1900. Same place. Bring the good bottle. Bring yourself.\n"
        "    — Bill.\n\n"
        "Underneath, in different ink: 'Don't be late. (You're always late.)'\n\n"
        "You stare at it. You absorb the implications. You will live with them.\n"
        "For approximately the next thirty seconds.\n\n"
        "Tigh's hand lands on your shoulder. You did not hear him approach. He\n"
        "smells like a fire that learned how to feel. His voice is very gentle\n"
        "and very sad.\n\n"
        "'Specialist. We are going to take a short walk to the airlock.'\n\n"
        "── ENDING: FORBIDDEN KNOWLEDGE (YOU READ THE FRAKKIN' LETTER) ──"
    )


def sealed_envelope_on_examine(world):
    if world.flags.get("opened_envelope"):
        return "Already opened. Already read. Already, very, very specifically not your business."
    return (
        "A standard officer-grade manila envelope. Sealed with red wax bearing the\n"
        "Galactica crest. Three words on the front, in red marker:\n\n"
        "    DO NOT OPEN.\n\n"
        "There is no addressee. There is no return address. There is only the\n"
        "wax, and the words, and you, and a decision to make."
    )


register_item(Item(
    id="sealed_envelope",
    name="sealed envelope",
    aliases=["envelope", "letter", "sealed envelope"],
    description="<dynamic>",
    takeable=True,
    on_use=sealed_envelope_on_use,
))


# ─── Worn copy of the Sacred Scrolls ─────────────────────────────────────────

register_item(Item(
    id="scrolls",
    name="worn copy of the Sacred Scrolls",
    aliases=["scrolls", "sacred scrolls", "book", "scripture", "scriptures", "pythia"],
    description=(
        "A worn-out copy of the Sacred Scrolls of Pythia. Cottle's name is in the\n"
        "front cover, crossed out. Roslin's name is below it, also crossed out, in\n"
        "Roslin's handwriting. Hadrian's name is below THAT, not crossed out,\n"
        "though Hadrian has no recollection of having owned a copy of the Sacred\n"
        "Scrolls and will say so if asked.\n\n"
        "The margins are filled with annotations. Every prophecy concerning a\n"
        "'dying leader' has been underlined three times. Every prophecy concerning\n"
        "anything ELSE has, next to it, a single handwritten word in furious\n"
        "block letters:\n\n"
        "    HACK.\n\n"
        "The word appears, by your count, two hundred and eleven times. Pythia is\n"
        "described, in a margin near the back, as 'a frakking hack.' The handwriting\n"
        "is not Roslin's. It is not Cottle's. It is, unmistakably, Tigh's."
    ),
    takeable=True,
))


# ─── Tyrol's missing wrench ──────────────────────────────────────────────────

def wrench_on_take_blocked(world):
    """Returned when the player attempts to take the wrench while Baltar is not
    distracted. The cmd_take handler can call this to deny pickup."""
    return (
        "You reach for the wrench. Baltar appears at your elbow as if conjured.\n\n"
        "'WHAT,' he says, in the tone of a man whose lab has just been violated,\n"
        "'are you doing, specialist. Put that DOWN. There is nothing in this lab\n"
        "that is for you. Put it DOWN.'\n\n"
        "He takes the wrench back. The wrench has, by Baltar's account, never\n"
        "existed."
    )


register_item(Item(
    id="wrench",
    name="Tyrol's wrench",
    aliases=["wrench", "tyrol's wrench"],
    description=(
        "A heavy, broken-in deck wrench. PROPERTY OF G. TYROL is stamped on the "
        "handle in three places. It has been used, you can tell, mostly to fix "
        "Vipers but occasionally — judging by a faint smear on the head — to fix "
        "people."
    ),
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


def _attach_other_dynamic_descriptions():
    from engine.registry import ITEMS as _ITEMS
    _ITEMS["photo_academy"]._dynamic_description = photo_on_examine  # type: ignore[attr-defined]
    _ITEMS["sealed_envelope"]._dynamic_description = sealed_envelope_on_examine  # type: ignore[attr-defined]


_attach_other_dynamic_descriptions()


# ─── Wrench: take-guard for Baltar's lab ──────────────────────────────────────


def _wrench_take_guard(world):
    """Block pickup unless Baltar is distracted (or not present in this room)."""
    # If we're not in Baltar's lab, no guard.
    if world.current_room != "baltars_lab":
        return None
    if world.flags.get("baltar_distracted"):
        return None
    return wrench_on_take_blocked(world)


def _attach_take_guards():
    from engine.registry import ITEMS as _ITEMS
    _ITEMS["wrench"]._take_guard = _wrench_take_guard  # type: ignore[attr-defined]


_attach_take_guards()

