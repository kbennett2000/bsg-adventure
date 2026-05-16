"""NPCs for the opening slice: Colonel Tigh, Crewman Hadrian."""

from engine.models import NPC
from engine.registry import register_npc
from engine.world import move_item_to_inventory


# ─── Colonel Tigh ──────────────────────────────────────────────────────────────

TIGH_WRONG_NAMES = [
    "Frakkin'... uh",
    "Specialist Frasier",
    "Tucker",
    "the toilet kid",
    "Specialist whats-her-face",
    "specialist whatever",
    "son",
    "you",
]


def _tigh_next_wrong_name(world) -> str:
    state = world.npc_state.setdefault("tigh", {})
    idx = state.get("wrong_name_index", 0)
    state["wrong_name_index"] = idx + 1
    return TIGH_WRONG_NAMES[idx % len(TIGH_WRONG_NAMES)]


def _tigh_give_quest(world) -> str:
    if world.flags.get("got_canteen"):
        return (
            "Tigh squints at you through the stall slats. 'You still here, specialist? "
            "ENGINEERING. THIRD VALVE. BRASS HANDLE. The one that, technically, doesn't "
            "exist. Now MOVE.'"
        )
    world.flags["got_canteen"] = True
    move_item_to_inventory(world, "canteen")
    first_wrong = _tigh_next_wrong_name(world)
    second_wrong = _tigh_next_wrong_name(world)
    return (
        "The stall door bangs open. Colonel Tigh is sitting fully clothed on a closed "
        "toilet, one eye on the door, the other somewhere in the past. He thrusts a "
        "battered metal canteen at you like it's a baby he's tired of holding.\n\n"
        "'What's your name again, son?'\n\n"
        f"'{world.player_name},' you say.\n\n"
        f"'Right. {first_wrong}. Listen up.' He shoves the canteen into your chest. "
        "'Take this. Down to Engineering. THIRD valve from the left. The one with the "
        "BRASS handle. The one that — officially — does not exist. Fill 'er up. Bring "
        "'er back. Do NOT open it. Do NOT smell it. Do NOT — and I cannot stress this "
        "enough — do NOT drink it.'\n\n"
        "He leans in. The fumes coming off him rearrange your hairline.\n\n"
        "'The frakkin' tide of command is coming in, specialist, and I am running dry "
        "on the high water mark. You read me?'\n\n"
        f"You nod. He nods. He has already forgotten you. 'Dismissed, {second_wrong}.'\n\n"
        "The stall door slams shut. From inside, very softly, you hear the Colonial "
        "Anthem being hummed off-key."
    )


TIGH_TOPICS = {
    "ship": (
        "Tigh gestures vaguely at the porcelain. 'She's a tough old girl. Built like my "
        "third wife. Built like my third wife's mother. BIGGER. Don't frakkin' print that.'"
    ),
    "adama": (
        "Tigh's face does something complicated. His one good eye gets misty. The other "
        "one becomes, briefly, MORE focused. 'Bill is — Bill is a fine commander. A FINE "
        "commander. I would take a frakkin' nuclear round in the throat for that man. "
        "Don't print THAT either.'"
    ),
    "commander": (
        "'The Old Man? FINE commander. FINE man. We — uh.' Tigh stares at a point on "
        "the bulkhead. 'We share a bond. A frakkin' BOND. Like brothers. Or — yeah. "
        "Brothers. Yeah. Move along.'"
    ),
    "bill": (
        "'WHAT ABOUT BILL.' Long pause. 'I mean. What about him. Nothing. Bill's fine. "
        "Bill is fine. Frak off.'"
    ),
    "water": (
        "'It is water.' His left eye twitches independently of his right. 'It IS water. "
        "Move along, son.'"
    ),
    "flask": (
        "'WHAT FRAKKIN' FLASK.' A long, dangerous silence. 'You see a flask, specialist? "
        "Do you SEE A FRAKKIN' FLASK.'"
    ),
    "canteen": (
        "'It's a CANTEEN, son. Like the regs say. Hydration. Crew readiness. Don't make "
        "this weird.'"
    ),
    "engineering": (
        "'Third valve. Brass handle. The one that does not exist. Are you frakkin' "
        "deaf, specialist?'"
    ),
    "cylons": (
        "'Toasters? On THIS deck? Don't be a frakkin' idiot, son. Now go mop something.'"
    ),
    "self": (
        f"Tigh stares at you for a long time. 'I forget your name.' Pause. 'Don't take "
        "it personally. I forget a lot of things on purpose.'"
    ),
    "starbuck": (
        "'Thrace? That one's gonna get someone frakked or fragged or both. Probably both. "
        "Stay out of her way, son.'"
    ),
    "baltar": (
        "Tigh's eye narrows. 'That man talks to himself. CONSTANTLY. In MY corridors. "
        "If he doesn't pipe down I'm gonna space the both of him.'"
    ),
}


def tigh_on_talk(world, topic):
    if topic is None:
        return _tigh_give_quest(world)
    for key, response in TIGH_TOPICS.items():
        if topic == key or key in topic or topic in key:
            return response
    return (
        f"Tigh stares at you. 'I don't know what the frak you're going on about, "
        f"{_tigh_next_wrong_name(world)}. Now MOVE. Brass handle. Third valve.'"
    )


register_npc(NPC(
    id="tigh",
    name="Colonel Tigh",
    aliases=["tigh", "colonel", "xo", "executive officer", "saul"],
    description=(
        "The XO. Sitting fully clothed on a closed toilet inside the middle stall, "
        "visible through the slats. He has the air of a man who is doing very important "
        "work that nobody can know about. The work appears to be 'drinking.'"
    ),
    on_talk=tigh_on_talk,
))


# ─── Crewman Hadrian ───────────────────────────────────────────────────────────

HADRIAN_RUMORS = [
    "'You hear about the Old Man and the XO? Three hours in his quarters yesterday. Door locked. THREE HOURS. I'm just sayin'.'",
    "'Word from deck five: Starbuck punched a chaplain. The chaplain blessed her fist back. Now they're best friends. The gods love a unit cohesion.'",
    "'My cousin works hangar deck. Says there's a deckhand on shift right now who's NEVER been on the duty roster. NEVER. You ever seen a deckhand who's not on the roster?'",
    "'Tigh's drinking water, sure. Sure. And I'm Number Frakkin' Six.'",
    "'Doc Cottle gave me a clean bill of health last week. Smoking the WHOLE TIME. Through his scrubs. I love that man.'",
    "'Baltar was in the head talking to nobody for forty-five minutes. I TIMED him. Forty-FIVE.'",
    "'You ever notice the new shift supervisor on deck twelve is, like, REALLY hot? Like, distractingly. Like — you know what, forget I said that.'",
    "'They moved the algae rations again. Pretty sure the rats are running an algae market now. Pretty sure the rats are UNIONIZED.'",
]


def hadrian_on_talk(world, topic):
    state = world.npc_state.setdefault("hadrian", {"rumor_index": 0, "told_about_xo": False})

    if topic in ("self", "name", "hadrian"):
        return (
            "'Name's Specialist Hadrian. Like the wall.' He pauses. 'Wait — you're "
            f"Specialist {world.player_name}? Hadrian. Like the WALL. We've been "
            "bunked next to each other for SIX MONTHS, frak's sake.'"
        )

    if topic in ("xo", "tigh", "colonel"):
        state["told_about_xo"] = True
        return (
            "'OH. Yeah. He's in the head. Has been for like, twenty minutes. He's "
            "got that LOOK. You know the look. The look where he's about to recite "
            "a poem about boats or order somebody spaced. He was asking after you.' "
            "He grins. 'Asking after SOMEBODY anyway. Probably you. He couldn't "
            "remember the name. Big shock.'"
        )

    if topic in ("xo's order", "order", "page", "intercom"):
        return (
            "'Yeah I heard. Whole deck heard. XO wants you in the head, on the double. "
            "Deck five. Try not to die. Try not to come back smelling like ambrosia, "
            "either, because then YOU'LL die, but slower.'"
        )

    if topic in ("apollo", "starbuck", "love triangle", "triangle"):
        return (
            "'Oh, THAT mess.' He shakes his head. 'Apollo and Starbuck are gonna get "
            "the whole fleet killed because somebody can't talk about their FEELINGS. "
            "There's a third party too, I hear. Cylon-shaped. Allegedly.'"
        )

    if topic in ("baltar",):
        return (
            "'Baltar was in the head talking to nobody for forty-five minutes. I "
            "TIMED him. Forty-FIVE. He came out and asked me if I was "
            "spying on him. I was eating a sandwich.'"
        )

    if topic in ("adama", "old man", "commander"):
        return (
            "'The Old Man? Good commander. Cryptic as a frakkin' temple oracle. Said "
            "something to me in the corridor last week — \"the depth of a man is the "
            "width of his ship\" — and walked off. I have been thinking about that "
            "every night since. I think it means nothing. I think it means EVERYTHING.'"
        )

    # Default: rotate through rumors
    rumor = HADRIAN_RUMORS[state["rumor_index"] % len(HADRIAN_RUMORS)]
    state["rumor_index"] += 1
    return rumor


register_npc(NPC(
    id="hadrian",
    name="Crewman Hadrian",
    aliases=["hadrian", "crewman", "bunkmate", "specialist hadrian"],
    description=(
        "Your bunkmate. Sprawled across the next rack over with a deck of cards and "
        "the relaxed posture of a man who has memorized every duty schedule and "
        "exploits all of them. Knows everyone's business. Smells faintly of recycled air "
        "and confidence."
    ),
    on_talk=hadrian_on_talk,
))
