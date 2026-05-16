"""All NPCs for the full game."""

from engine.commands import HandlerResult, trigger_ending
from engine.models import NPC
from engine.registry import register_npc
from engine.world import bump_stat, get_stat, move_item_to_inventory, move_item_to_room


# ─── Romance state machine ─────────────────────────────────────────────────────
# Each romance NPC has 3 escalating beats; beat 4 = "it's complicated" terminal.
# Starting a 3rd simultaneous flirtation triggers the love-quadrangle ending.

ROMANCE_NPCS = {"starbuck", "six", "helo", "dualla"}

ROMANCE_DISPLAY_NAMES = {
    "starbuck": "Lieutenant Thrace",
    "six": "your shift supervisor",
    "helo": "Captain Agathon",
    "dualla": "Petty Officer Dualla",
}


def _bump_romance(world, npc_id):
    """Advance a flirtation by one beat. Returns one of:
        'quadrangle'   — third unique partner; trigger the quadrangle ending
        'complicated'  — this NPC just hit beat 4 (locked out)
        'already_done' — this NPC was already at the terminal beat
        'beat1'/'beat2'/'beat3' — normal progression
    """
    assert npc_id in ROMANCE_NPCS, f"unknown romance npc: {npc_id}"
    actives = world.flags.setdefault("active_romances", [])
    key = f"romance_{npc_id}"
    cur = world.flags.get(key, 0)

    if cur >= 4:
        return "already_done"

    if cur == 0:
        if len(actives) >= 2 and npc_id not in actives:
            return "quadrangle"
        if npc_id not in actives:
            actives.append(npc_id)

    new = cur + 1
    world.flags[key] = new

    if new >= 4:
        if npc_id in actives:
            actives.remove(npc_id)
        return "complicated"

    return f"beat{new}"


def _love_quadrangle_ending(world, would_be_third) -> HandlerResult:
    actives = list(world.flags.get("active_romances", []))
    a = ROMANCE_DISPLAY_NAMES.get(actives[0], actives[0]) if actives else "someone"
    b = ROMANCE_DISPLAY_NAMES.get(actives[1], actives[1]) if len(actives) > 1 else "someone else"
    c = ROMANCE_DISPLAY_NAMES.get(would_be_third, would_be_third)
    return trigger_ending(
        world,
        "love_quadrangle",
        f"Three weeks pass. You do not remember most of them.\n\n"
        f"What you DO remember is the moment {a} found {b}'s sidearm in your rack.\n"
        f"And the moment {b} found {a}'s comb in your kit. And the moment {c}, who\n"
        f"had been hoping to be the next entry, found the previous two having a\n"
        f"private conversation about you in a corridor.\n\n"
        f"At 1600 hours, you receive a single new posting on your tablet:\n\n"
        f"  PERMANENT LATRINE DUTY. DECK FIVE.\n"
        f"  AND DECK SEVEN. AND DECK TWELVE.\n"
        f"  AND ALSO, FOR REASONS NOBODY WILL EXPLAIN,\n"
        f"  ADMIRAL ADAMA'S PRIVATE HEAD.\n"
        f"  STARTING IMMEDIATELY.\n\n"
        f"Apollo, on his way past, claps you on the shoulder. 'Brutal. Good luck,\n"
        f"specialist.' He has no idea what is happening. He is, somehow, the most\n"
        f"innocent person in this entire affair.\n\n"
        f"You salute. Nobody returns it.\n"
        f"You frak. Loudly. Out loud.\n"
        f"You eat an algae bar.\n"
        f"You start mopping.\n\n"
        f"── ENDING: LOVE QUADRANGLE (PERMANENT LATRINE DUTY) ──"
    )


def _romance_apply(world, npc_id, beat_texts, complicated_text):
    """Helper that performs the bump and returns the right response text or ending.

    beat_texts: list of three strings for beat1/2/3
    complicated_text: string for the 'it's complicated' terminal beat
    """
    result = _bump_romance(world, npc_id)
    if result == "quadrangle":
        return _love_quadrangle_ending(world, npc_id)
    if result == "complicated":
        bump_stat(world, "suspicion", 5)  # word gets around
        return complicated_text
    if result == "already_done":
        return complicated_text
    if result.startswith("beat"):
        idx = int(result[-1]) - 1
        return beat_texts[idx]
    return beat_texts[0]  # fallback


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

# Topics that, asked of Tigh, raise the player's global SUSPICION stat. At 75+,
# he spaces them next time they talk.
TIGH_DANGER_TOPICS = {"flask", "water", "adama", "bill", "commander", "meeting", "meetings", "quarters"}
TIGH_SUSPICION_BUMP = 25
TIGH_SPACE_THRESHOLD = 75


def _tigh_next_wrong_name(world) -> str:
    state = world.npc_state.setdefault("tigh", {})
    idx = state.get("wrong_name_index", 0)
    state["wrong_name_index"] = idx + 1
    return TIGH_WRONG_NAMES[idx % len(TIGH_WRONG_NAMES)]


def _tigh_should_space(world) -> bool:
    return get_stat(world, "suspicion") >= TIGH_SPACE_THRESHOLD


def _tigh_spaced_ending(world) -> HandlerResult:
    return trigger_ending(
        world,
        "spaced",
        "Tigh sets down the canteen. He sets down the not-flask. He stands up. He is\n"
        "very still. His one good eye fills, slowly, with something that looks almost\n"
        "like grief.\n\n"
        f"'I'm sorry, {_tigh_next_wrong_name(world)}.' His voice is gentle for the first\n"
        "time in years. 'I really am. But you've got a face like a man who has been\n"
        "doing addition. And I cannot have you doing addition. Not about me. Not about\n"
        "Bill. Not about the meetings.'\n\n"
        "He keys the intercom. 'Tyrol. I need a Specialist escorted to the port-side\n"
        "airlock. Hadrian's bunkmate. Yeah. Yeah, the one.'\n\n"
        "He looks at you. His eye is wet. He is genuinely sad.\n\n"
        "'For what it's worth, son, you were a fine frakkin' specialist.'\n\n"
        "The Chief is here. The airlock is here. Space is here.\n\n"
        "You are not.\n\n"
        "── ENDING: SPACED FOR KNOWING TOO MUCH ABOUT TIGH'S DRINKING ──"
    )


TIGH_DEJA_VU = (
    "Tigh stops mid-sip. He stares at you through the stall slats. His one good eye\n"
    "narrows.\n\n"
    "'Have I — have I given you this canteen before, son? I feel like I have. I feel\n"
    "like I have given you this canteen MORE than once. That can't be right. That\n"
    "would be a frakkin' time loop. There is no frakkin' time loop. That'd be a\n"
    "regulation violation. The regs are very clear on time loops.'\n\n"
    "He shakes it off. He always shakes it off."
)


def _tigh_give_quest(world):
    # Once Tigh's suspicion is high, the next default talk triggers the spaced ending.
    if _tigh_should_space(world):
        return _tigh_spaced_ending(world)
    deja = _ng_plus_deja_vu(world, "tigh", TIGH_DEJA_VU)
    if world.flags.get("got_canteen"):
        return deja + (
            "Tigh squints at you through the stall slats. 'You still here, specialist? "
            "ENGINEERING. THIRD VALVE. BRASS HANDLE. The one that, technically, doesn't "
            "exist. Now MOVE.'"
        )
    world.flags["got_canteen"] = True
    move_item_to_inventory(world, "canteen")
    if "napkin" not in world.inventory and "napkin" not in world.room_items.get("head_deck_5", []):
        move_item_to_room(world, "napkin", "head_deck_5")
    first_wrong = _tigh_next_wrong_name(world)
    second_wrong = _tigh_next_wrong_name(world)
    return deja + (
        "The stall door bangs open. Colonel Tigh is sitting fully clothed on a closed "
        "toilet, one eye on the door, the other somewhere in the past. He thrusts a "
        "battered metal canteen at you like it's a baby he's tired of holding. A "
        "crumpled napkin falls out of his lap and skitters under the partition. He "
        "doesn't notice.\n\n"
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
    "meeting": (
        "Tigh's face shuts. His shoulders square. 'COMMAND meetings are CLASSIFIED, "
        "Specialist. You don't ask about command meetings. You don't IMAGINE command "
        "meetings. There are no command meetings. There never WERE command meetings.'"
    ),
    "meetings": (
        "Tigh's face shuts. His shoulders square. 'COMMAND meetings are CLASSIFIED, "
        "Specialist. Frak. OFF.'"
    ),
    "quarters": (
        "'The Old Man's QUARTERS are need-to-know, son.' He stares at the bulkhead. "
        "'And you do NOT need to know.'"
    ),
    "canteen": (
        "'It's a CANTEEN, son. Like the regs say. Hydration. Crew readiness. Don't make "
        "this weird.'"
    ),
    "napkin": (
        "Tigh's eye widens. He pats his pockets. He pats his other pockets. 'WHAT "
        "frakkin' napkin. There IS no napkin. THERE IS NO NAPKIN, SPECIALIST.'"
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
    if _tigh_should_space(world):
        return _tigh_spaced_ending(world)

    if topic is None:
        bump_stat(world, "morale", -2)  # he's a lot
        return _tigh_give_quest(world)

    topic_lower = topic.lower()
    if any(danger in topic_lower or topic_lower in danger for danger in TIGH_DANGER_TOPICS):
        bump_stat(world, "suspicion", TIGH_SUSPICION_BUMP)
        # Check threshold immediately so a 4th sensitive question doesn't get a chatty reply.
        if _tigh_should_space(world):
            return _tigh_spaced_ending(world)

    for key, response in TIGH_TOPICS.items():
        if topic == key or key in topic or topic in key:
            return response

    return (
        f"Tigh stares at you. 'I don't know what the frak you're going on about, "
        f"{_tigh_next_wrong_name(world)}. Now MOVE. Brass handle. Third valve.'"
    )


def _tigh_receive_stash_bottle(world):
    """Returning one of the stash bottles to Tigh. Track count; on the third return,
    he acknowledges you with a swig — completing the stash side quest."""
    state = world.npc_state.setdefault("tigh", {})
    returned = state.get("stash_returned", 0) + 1
    state["stash_returned"] = returned
    # Bump suspicion either way — he KNOWS you've been finding his hiding spots.
    bump_stat(world, "suspicion", 4)
    if returned >= 3:
        world.flags["quest_stash_complete"] = True
        bump_stat(world, "morale", 8)
        bump_stat(world, "exhaustion", 6)
        return (
            "Tigh stares at the bottle in your hand. Then at the empty space where\n"
            "two more bottles used to be. Then at you. His one good eye narrows to\n"
            "a slit. He says nothing for a long, dangerous moment.\n\n"
            "Then he laughs. It is a small, raw, surprising laugh.\n\n"
            "'Well, frak ME, specialist. You found 'em. All three. You found EVERY\n"
            "frakkin' one. I had a fourth, you know. I had a fourth and I'm not\n"
            "tellin' you where it is. But you did the work. You did the WORK.'\n\n"
            "He takes the bottle from you. He takes a long, expressive pull. Then\n"
            "he hands it back. The bottle is, somehow, only slightly less full.\n\n"
            "'Have a swig, son. Have a frakkin' swig. You earned it. Don't make me\n"
            "regret this.'"
        )
    return (
        "Tigh takes the bottle from you. He weighs it. He squints at you. He squints\n"
        "harder.\n\n"
        f"'Where in the cosmic FRAK did you find THIS one, {_tigh_next_wrong_name(world)}.'\n\n"
        "He does not, you note, deny that it's his. He does not, you note, ask for\n"
        "the others. He sets the bottle down on the toilet tank like he's filing a\n"
        "report. He looks at you for a long, evaluative second. Then he turns away."
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
    on_give={
        "flask": _tigh_receive_stash_bottle,
        "stash_bottle_mess": _tigh_receive_stash_bottle,
        "stash_bottle_hangar": _tigh_receive_stash_bottle,
    },
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
    # The "two decks at once" rumor — the user-spec'd discoverability hint for
    # the hidden Cylon resurrection mechanic.
    "'OK this one is weird. There's a specialist — I'm not gonna name names — who got SEEN on TWO DECKS AT ONCE last week. Two people, two different decks, same specialist, same time. I keep thinkin' about it. I shouldn't keep thinkin' about it. I keep thinkin' about it.'",
]


def _ng_plus_deja_vu(world, npc_id: str, line: str) -> str:
    """Returns the déjà vu prefix the first time the player engages this NPC in
    a new-game-plus run; empty string otherwise."""
    if not world.flags.get("ng_plus"):
        return ""
    state = world.npc_state.setdefault(npc_id, {})
    if state.get("ng_plus_acknowledged"):
        return ""
    state["ng_plus_acknowledged"] = True
    return line + "\n\n"


HADRIAN_DEJA_VU = (
    "He squints. He squints harder. He sets down the cards.\n\n"
    "'Wait. Wait wait wait. Have we — have we DONE this before? Have we had this\n"
    "EXACT conversation before? I just got the weirdest frakkin' sense of —\n"
    "never mind. Never mind. Reincarnation is a frakkin' hack. Pythia said that.\n"
    "Pythia would've said that if Pythia weren't a frakkin' hack.'\n\n"
    "(He recovers. He always recovers.)"
)


HADRIAN_SUSPICIOUS_PREFIX = (
    "Hadrian sets the cards down. He looks at you. He looks at you for a beat\n"
    "longer than is friendly. He picks the cards back up. He shuffles them. He\n"
    "watches you over the top of the eight of swords.\n\n"
    "'You been... around, lately?' He doesn't say it like a question. 'You been\n"
    "ON deck five. The WHOLE time. Right?'\n\n"
    "(He recovers. Mostly.)"
)


def hadrian_on_talk(world, topic):
    state = world.npc_state.setdefault("hadrian", {"rumor_index": 0})
    bump_stat(world, "morale", 2)  # fraternizing always helps

    deja = _ng_plus_deja_vu(world, "hadrian", HADRIAN_DEJA_VU) if topic is None else ""

    # Cylon-resurrection world drift: after resurrection #1, Hadrian acts
    # suspicious of his bunkmate. Fires once.
    if (world.flags.get("npc_suspicious_hadrian")
            and not state.get("acknowledged_suspicion")
            and topic is None):
        state["acknowledged_suspicion"] = True
        deja = HADRIAN_SUSPICIOUS_PREFIX + "\n\n"

    if topic in ("self", "name", "hadrian"):
        return (
            "'Name's Specialist Hadrian. Like the wall.' He pauses. 'Wait — you're "
            f"Specialist {world.player_name}? Hadrian. Like the WALL. We've been "
            "bunked next to each other for SIX MONTHS, frak's sake.'"
        )

    if topic in ("xo", "tigh", "colonel"):
        return (
            "'OH. Yeah. He's in the head. Has been for like, twenty minutes. He's "
            "got that LOOK. You know the look. The look where he's about to recite "
            "a poem about boats or order somebody spaced. He was asking after you. "
            "Asking after SOMEBODY anyway. Probably you. He couldn't remember the "
            "name. Big shock.'"
        )

    if topic in ("xo's order", "order", "page", "intercom"):
        return (
            "'Yeah I heard. Whole deck heard. XO wants you in the head, on the double. "
            "Deck five. Try not to die. Try not to come back smelling like ambrosia, "
            "either, because then YOU'LL die, but slower.'"
        )

    if topic in ("jump", "ftl", "coordinates", "coords"):
        world.flags["heard_hadrian_jump_gossip"] = True
        return (
            "'Yeah, the fleet's jumping. Soon. Tonight? Tomorrow? Could be five minutes "
            "from now. Could be never. The CIC ensigns are losing their frakkin' minds "
            "though, so somebody up there knows something. I asked the XO. The XO told "
            "me to mop something. The mop was already wet. I love this job.'"
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

    if topic in ("six", "cylon", "supervisor"):
        return (
            "'Listen, I'm not SAYING all the suspiciously-hot blondes are toasters. "
            "I'm SAYING the math is suspicious. And the math is doing PUSHUPS, my "
            "friend. The math is doing pushups.'"
        )

    if topic in ("adama", "old man", "commander"):
        return (
            "'The Old Man? Good commander. Cryptic as a frakkin' temple oracle. Said "
            "something to me in the corridor last week — \"the depth of a man is the "
            "width of his ship\" — and walked off. I have been thinking about that "
            "every night since. I think it means nothing. I think it means EVERYTHING.'"
        )

    if topic in ("roslin", "president"):
        return (
            "'Roslin? Good woman. Strong woman. Definitely-not-dying woman. She keeps "
            "asking everybody if they're hiding a prophecy. ME, even. ME. I was eating "
            "lasagna. Why would I be hiding a prophecy in a lasagna? Although. Hmm.'"
        )

    if topic in ("stash", "tigh's stash", "bottles", "bottle", "the stash"):
        return (
            "'Oh, you want the XO's stash?' He laughs. 'Wait til NIGHT, frak's sake.\n"
            "Tigh hits the deck around the start of the Dog Watch and by Night he's\n"
            "face-down. You go poking around DAYTIME and he'll have you peeling deck\n"
            "plates with your teeth. Night, specialist. Night.'"
        )

    if topic in ("cards", "triad", "cards night", "starbuck's cards"):
        return (
            "'Cards night? Pilots do triad in the AFTERNOON. Mornings they're hung\n"
            "over, evenings they're back in their racks pretending to read regs.\n"
            "Afternoons. You sit down with Thrace, you lose your shift bonuses, you\n"
            "go home a wiser man. Or, in your case, a SOMEWHAT wiser man.'"
        )

    if topic in ("schedule", "watches", "watch", "shifts", "the day"):
        return (
            "'Five watches. Morning Watch, Forenoon, Afternoon, Dog Watch, Night.\n"
            "Repeat until you die. Mess is Morning and Afternoon only, so don't\n"
            "sleep through if you wanna eat. Officers do paperwork on Forenoon,\n"
            "drink on Dog Watch, and bother Adama all Night. The XO is in the head\n"
            "the entire frakkin' time, somehow, in defiance of physics and biology.'"
        )

    rumor = HADRIAN_RUMORS[state["rumor_index"] % len(HADRIAN_RUMORS)]
    state["rumor_index"] += 1
    return deja + rumor


register_npc(NPC(
    id="hadrian",
    name="Crewman Hadrian",
    aliases=["hadrian", "crewman", "bunkmate", "specialist hadrian"],
    description=(
        "Your bunkmate. Sprawled across the next rack over with a deck of cards and "
        "the relaxed posture of a man who has memorized every duty schedule and "
        "exploits all of them. Knows everyone's business. Smells faintly of recycled "
        "air and confidence."
    ),
    on_talk=hadrian_on_talk,
))


# ─── Admiral Adama ─────────────────────────────────────────────────────────────

ADAMA_PROVERBS = [
    "'A ship is only as strong as the men who hate each other on it.'",
    "'Sometimes, the duty IS the man. Sometimes, the man is the duty. Most of the time, neither.'",
    "'There are three kinds of officers in this fleet, son: the dead, the dying, and the lucky. Same thing.'",
    "'A jump is just a long blink. A war is just a long jump. A life is just a long war. Don't quote me.'",
    "'Frak is a verb, son. So is duty. So is faith. So is the other thing.'",
    "'Steel remembers. Water forgets. We are mostly water.'",
    "'You can lead a Viper to a launch tube, but you cannot make her jump.'",
    "'The depth of a man is the width of his ship. The width of his ship is the depth of his man.'",
    "'A specialist mops. A captain commands. A god watches. Two of those three I've met.'",
    "'There are no atheists in jump tubes.'",
]


def _adama_proverb(world) -> str:
    state = world.npc_state.setdefault("adama", {})
    idx = state.get("proverb_index", 0)
    p = ADAMA_PROVERBS[idx % len(ADAMA_PROVERBS)]
    state["proverb_index"] = idx + 1
    return p


def _adama_hero_ending(world) -> HandlerResult:
    return trigger_ending(
        world,
        "hero",
        "You hold out the napkin.\n\n"
        "Admiral Adama looks at it. He looks at you. He looks at the napkin. He looks\n"
        "at the plot. He takes the napkin between two fingers like it is a wounded\n"
        "bird. He reads it. He reads it again. He hands it to an ensign without\n"
        "looking. The ensign's hands shake. The ensign types. The plot fills in.\n\n"
        "'Mister Gaeta. Set vector. Authorize jump.'\n\n"
        "'Aye, sir.'\n\n"
        "'In thirty seconds, on my mark.'\n\n"
        "'Aye, sir.'\n\n"
        "The Old Man turns to you. For one full second he holds eye contact. He sees\n"
        "you. He really sees you. Something passes across his face that might be\n"
        "gratitude, or might be gas. He nods, exactly once.\n\n"
        f"'Good work,' he says. 'Specialist...?'\n\n"
        f"'{world.player_name},' you say.\n\n"
        "'Right. Specialist.' He has already forgotten. 'Dismissed.'\n\n"
        "The fleet jumps around you. You are still standing in CIC. Nobody asks you\n"
        "to leave. Nobody asks you to stay. You did it. You saved the fleet. The fleet\n"
        "does not know. The fleet will never know.\n\n"
        "You feel fine about that. You feel, in fact, frakkin' great.\n\n"
        "── ENDING: HERO (ACCIDENTAL) ──"
    )


def _adama_receive_napkin(world):
    if not world.flags.get("realized_napkin_is_coords"):
        return (
            "Admiral Adama takes the napkin between two fingers. He squints at it. "
            "He turns it over. He hands it back to you without comment. 'Specialist. "
            "Some napkins are just napkins.' He turns away. You are dismissed without "
            "having been acknowledged."
        )
    # Stat gates: a suspicious specialist doesn't get the win; an exhausted one collapses.
    suspicion = get_stat(world, "suspicion")
    exhaustion = get_stat(world, "exhaustion")
    if suspicion >= 75:
        return trigger_ending(
            world,
            "spaced",
            "You hold out the napkin.\n\n"
            "Admiral Adama looks at it. He looks at you. He looks, very deliberately,\n"
            "across CIC, where an MP is standing very still. He nods, just once. The\n"
            "MP starts walking. They have somehow always been here.\n\n"
            "'Take whatever this is,' Adama says, handing the napkin away without\n"
            "looking, 'to the XO. With my compliments. And take the specialist with\n"
            "you.'\n\n"
            "The MPs are professional. Tigh is, on the way, almost apologetic. The\n"
            "airlock is short. The ceremony is shorter.\n\n"
            "── ENDING: SPACED (THEY DIDN'T TRUST YOU) ──"
        )
    if exhaustion >= 80:
        # Player faints; napkin is lost in the shuffle; force collapse-style outcome.
        return (
            "You hold out the napkin. Or you try to. Your arm is heavier than your "
            "arm has any business being. The napkin slips. The napkin lands. The "
            "deck rises to meet you with the specific patience of a deck that has "
            "met a lot of specialists this way.\n\n"
            "Somewhere very far away, an ensign picks up the napkin and frowns at "
            "it. 'Sir, this is a — this is a recipe.'\n\n"
            "You will wake up in sickbay. The fleet will jump without you. You will "
            "be fine. Probably."
        )
    return _adama_hero_ending(world)


ADAMA_DEJA_VU = (
    "He does not turn. He speaks as if he had been about to.\n\n"
    "'Specialist. We have not met. We have, however, conferred. I do not know how\n"
    "I know that. The scriptures are quiet on the matter. I trust the scriptures\n"
    "less than I trust my own discomfort. My discomfort is, currently, you.'\n\n"
    "He turns. Just to look at you. Just for a second. The look is, in its way,\n"
    "the most acknowledgement you will ever get from this man."
)


def adama_on_talk(world, topic):
    bump_stat(world, "morale", -2)  # standing at attention takes it out of you

    if topic is None:
        deja = _ng_plus_deja_vu(world, "adama", ADAMA_DEJA_VU)
        return deja + (
            "Admiral Adama turns, slowly, like a turret. He fixes you with a look "
            "that has seen seventeen wars and is unimpressed by yours.\n\n"
            f"'{_adama_proverb(world)}'\n\n"
            "He turns back to the plot."
        )

    topic_lower = topic.lower()
    if topic_lower in ("self", "name", "me"):
        return (
            "He does not turn around. 'I do not know your name, specialist. I do not "
            "intend to learn it. That is not personal. That is rank discipline.'"
        )
    if topic_lower in ("jump", "ftl", "coordinates", "coords"):
        world.flags["heard_adama_jump_prep"] = True
        return (
            "'The fleet jumps when the fleet jumps, specialist. The coordinates are "
            "the XO's responsibility. The XO is... indisposed. I am waiting.' He "
            "stares at the empty coordinate field on the plot. The empty field stares "
            "back."
        )
    if topic_lower in ("tigh", "xo", "colonel"):
        return (
            "Adama does not move. 'The XO is a fine officer. The XO is my finest "
            "officer. The XO is, at the moment, in the head. He will be along. He "
            "always is.'"
        )
    if topic_lower in ("napkin",):
        if "napkin" in world.inventory:
            return (
                "Adama does not look at the napkin. He has not been told to. 'If you "
                "have something for me, Specialist, give it to me.'"
            )
        return (
            "'I do not know about a napkin, specialist. There are many napkins on "
            "this ship. They are all napkins. Some of them are wet.'"
        )
    if topic_lower in ("cylon", "cylons", "toasters"):
        return (
            "Adama's jaw tightens. 'There are no Cylons on this ship.' Long pause. "
            "He says it again, more quietly, as if convincing himself. 'There are no "
            "Cylons on this ship.'"
        )
    if topic_lower in ("six", "blonde", "supervisor"):
        return (
            "'I do not concern myself with the personal lives of my supervisors, "
            "specialist. I concern myself with the personal lives of my pilots, "
            "because the gods know nobody else will.'"
        )
    if topic_lower in ("prophecy", "pythia", "scriptures"):
        return (
            "Adama exhales. 'The President has been spending too much time in "
            "sickbay with the scriptures. I do not put stock in prophecy. I put "
            "stock in coordinates. The coordinates are not arriving.'"
        )
    return f"'{_adama_proverb(world)}' He does not elaborate. He never elaborates."


register_npc(NPC(
    id="adama",
    name="Admiral Adama",
    aliases=["adama", "admiral", "old man", "bill", "commander"],
    description=(
        "The Old Man. Standing at the central plot with his hands clasped behind "
        "his back, looking at a coordinate field that is, conspicuously, empty. He "
        "has the bearing of a man who has been gracefully patient for forty years "
        "and is approximately three minutes from no longer being patient."
    ),
    on_talk=adama_on_talk,
    on_give={"napkin": _adama_receive_napkin},
))


# ─── Starbuck ──────────────────────────────────────────────────────────────────


def _starbuck_rotate_mood(world):
    state = world.npc_state.setdefault("starbuck", {"mood_index": 0})
    moods = ["fight", "frak", "punch_bulkhead"]
    mood = moods[state["mood_index"] % len(moods)]
    state["mood_index"] += 1
    state["mood"] = mood
    return mood


def starbuck_on_talk(world, topic):
    bump_stat(world, "morale", 4)
    if topic is None:
        mood = _starbuck_rotate_mood(world)
        if mood == "fight":
            return (
                "Starbuck looks up from her cards. She sizes you up like she's deciding\n"
                "whether you'd fold easy. 'You. Specialist. I got triad, I got arm\n"
                "wrestling, I got making out. PICK ONE. I haven't got all frakkin' day.'"
            )
        if mood == "frak":
            return (
                "Starbuck looks up. Her grin is the kind that has ended marriages.\n"
                "'You. Specialist. Have I seen you before? Doesn't matter. I got triad,\n"
                "I got arm wrestling, I got making out. The making out is the special\n"
                "today. PICK ONE.'"
            )
        # punch_bulkhead
        return (
            "Starbuck is not looking at you. Starbuck is looking at a bulkhead. She\n"
            "throws a punch. The bulkhead does not punch back. This appears to make\n"
            "her angrier. Without turning, she says: 'You want something, specialist?\n"
            "Triad. Arm wrestling. Making out. Pick. One.'"
        )

    topic_lower = topic.lower()

    if topic_lower in ("triad", "cards"):
        # Cards Night is Afternoon only. Outside the window, Starbuck deflects
        # in-character (no error message).
        AFTERNOON = 2
        if not world.flags.get("quest_cards_started") and world.shift != AFTERNOON:
            return (
                "She blows a smoke ring. 'Cards night, specialist? Not this watch.\n"
                "Triad's an AFTERNOON thing. I haven't even pretended to do paperwork\n"
                "yet. Come back when the sun's somewhere it wouldn't be on Caprica.'"
            )
        # First-time cards triggers the quest with a choice menu in-character.
        if not world.flags.get("quest_cards_started"):
            world.flags["quest_cards_started"] = True
            bump_stat(world, "morale", 3)
            return (
                "'Sit down.' She deals. The cards come out crooked because she shuffles\n"
                "like she's beating somebody up. Three rounds in, she discovers you have\n"
                "no money. She does not, technically, care.\n\n"
                "'Here's the question, specialist. You're gonna lose. We both know\n"
                "you're gonna lose. The only question is HOW you're gonna lose. You can\n"
                "lose GRACEFUL. You can lose FLIRTY. You can CHEAT, which you will be\n"
                "bad at, which I will catch. You can ACCUSE ME of cheating, which is\n"
                "honestly the most interesting option. Pick. One.'\n\n"
                "(Pick one: graceful, flirt, cheat, or accuse.)"
            )
        if world.flags.get("quest_cards_resolved"):
            return (
                "'We already played, specialist. Stop pawing at the deck. I am not\n"
                "running this hand twice for free.'"
            )
        return (
            "'Pick, specialist. Graceful, flirt, cheat, or accuse. I'm not getting\n"
            "any younger and I haven't dealt the second hand.'"
        )

    if topic_lower in ("graceful", "lose graceful", "gracefully"):
        if not world.flags.get("quest_cards_started"):
            return "She squints. 'Graceful WHAT, specialist. Ask me to play cards first.'"
        if world.flags.get("quest_cards_resolved"):
            return "'Already played, specialist. You played graceful. We are NOT replaying.'"
        world.flags["quest_cards_resolved"] = True
        world.flags["quest_cards_choice"] = "graceful"
        bump_stat(world, "morale", 5)
        return (
            "You lose. You lose well. You shake her hand. You tip your imaginary cap.\n\n"
            "She nods, slowly. 'Class, specialist. Class. Most pilots can't manage\n"
            "this. Most pilots manage badly. You did the thing.'\n\n"
            "She does not, you note, kiss you. She does not, you note, hit on you.\n"
            "She does, you note, look at you for an extra half-second when she says\n"
            "'class.' Some part of you is hopeful. Some part of you knows better."
        )

    if topic_lower in ("flirt", "lose flirty", "flirty"):
        if not world.flags.get("quest_cards_started"):
            return "She raises an eyebrow. 'Flirt WHAT, specialist. Start a game first.'"
        if world.flags.get("quest_cards_resolved"):
            return "'Already played, specialist.'"
        world.flags["quest_cards_resolved"] = True
        world.flags["quest_cards_choice"] = "flirt"
        bump_stat(world, "morale", 7)
        # Bump romance, but don't trigger ending here (single bump).
        result = _romance_apply(
            world,
            "starbuck",
            beat_texts=[
                "You lose every hand. You lose them WITH FEELING. You look up over your\n"
                "cards. You hold her gaze. You play one specific bad card with very\n"
                "specific eye contact.\n\n"
                "She laughs out loud. 'OH. OH, specialist. Smooth. Smooth-ish. I'll\n"
                "TAKE smooth-ish.'\n\n"
                "She kicks Apollo's chair out from under him without looking. Apollo\n"
                "lands hard. Apollo deserved it. Apollo's expression is doing a lot.",
                "You lose. You lose flirtatiously. She kisses you across the table.\n"
                "Apollo makes a wet noise.",
                "You lose. She kisses you again. Apollo has, by this point, left the\n"
                "rec room.",
            ],
            complicated_text=(
                "She looks at you over the cards. 'Specialist. Listen. The flirting was\n"
                "fun. The flirting was REAL fun. The flirting is, also, over. Apollo\n"
                "is sulking in a Viper and somebody has to go pry him out. That somebody\n"
                "is me. Go find a better problem.'"
            ),
        )
        return result

    if topic_lower in ("cheat", "lose cheating"):
        if not world.flags.get("quest_cards_started"):
            return "She narrows her eyes. 'Cheat WHAT, specialist. Cards first.'"
        if world.flags.get("quest_cards_resolved"):
            return "'Already played, specialist. You got caught. Move along.'"
        world.flags["quest_cards_resolved"] = True
        world.flags["quest_cards_choice"] = "cheat"
        bump_stat(world, "morale", -15)  # public humiliation lands hard
        bump_stat(world, "suspicion", 12)
        return (
            "You attempt to palm a card. Starbuck has been watching you palm the\n"
            "card from approximately the moment the card existed. She watches the\n"
            "palm. She watches the un-palm. She watches the desperate hide-the-palm\n"
            "shuffle. She watches you sweat.\n\n"
            "'WOW,' she says. 'Wow. Specialist. That was BAD. That was historically\n"
            "bad. I have to tell Apollo about that. I have to tell EVERYONE about\n"
            "that. The bridge crew is going to hear about that. The bridge crew is\n"
            "going to TELL the deck crew. You are GOING TO BE a story, specialist.'\n\n"
            "Apollo is laughing. Apollo cannot stop laughing. You walk away. The\n"
            "laughing continues until you reach the corridor."
        )

    if topic_lower in ("accuse", "accuse her", "accuse starbuck"):
        if not world.flags.get("quest_cards_started"):
            return "She tilts her head. 'Accuse WHO of WHAT, specialist. Cards first.'"
        if world.flags.get("quest_cards_resolved"):
            return "'Already played. We had words. We're done.'"
        world.flags["quest_cards_resolved"] = True
        world.flags["quest_cards_choice"] = "accuse"
        bump_stat(world, "morale", 6)
        # Burn the Starbuck romance to "complicated" — she respects the move but it kills it.
        # Force the romance to its terminal state.
        actives = world.flags.setdefault("active_romances", [])
        if "starbuck" in actives:
            actives.remove("starbuck")
        world.flags["romance_starbuck"] = 4
        return (
            "You set your cards down. You meet her eyes. You say, very evenly,\n"
            "'You're cheating, Lieutenant.'\n\n"
            "The rec room goes silent. Apollo stops breathing. A pilot at the next\n"
            "table puts down a sandwich.\n\n"
            "Starbuck stares at you. For one full second. For another full second.\n"
            "Then she throws her head back and LAUGHS, loud and real.\n\n"
            "'OH. OH I LIKE you, specialist. I LIKE you. You're correct. Of course\n"
            "I'm cheating. I have been cheating since I was eight. Pilots cheat. It's\n"
            "in the regs.'\n\n"
            "She gathers the cards in one motion. 'You and me, specialist? Not gonna\n"
            "happen. We respect each other too much. Go away. I have to start cheating\n"
            "AT Apollo, who has noticed nothing so far.'"
        )

    if topic_lower in ("arm wrestling", "arm", "wrestle", "wrestling"):
        bump_stat(world, "morale", 3)
        bump_stat(world, "exhaustion", 5)  # she dislocates something
        return (
            "She slams her elbow on the table. You slam yours. You make contact. The\n"
            "fight lasts approximately one half of one second. She does not break a\n"
            "sweat. Your arm is now a different shape than it was. 'Better, specialist.\n"
            "I respect that.' She is already looking at someone else. 'NEXT.'"
        )

    if topic_lower in ("making out", "make out", "kiss", "kissing"):
        bump_stat(world, "morale", 10)
        return _romance_apply(
            world,
            "starbuck",
            beat_texts=[
                # beat 1 — the canonical kiss
                "She raises an eyebrow. She raises THE eyebrow. From across the room,\n"
                "Apollo makes a noise that is half whimper and half wedding vow.\n\n"
                "Starbuck stands up. She walks over. She kisses you. It lasts six full\n"
                "seconds. It tastes like cigars, ambrosia, and very specifically a future\n"
                "she has already decided is not yours. She steps back. She wipes her\n"
                "mouth with the back of her hand.\n\n"
                "'You can go now, specialist.' She has already forgotten you.\n\n"
                "Apollo is staring. Apollo's mouth is open. Apollo will need a moment.",
                # beat 2
                "She looks up from her cards. 'Back, huh.' She tilts her head. She's\n"
                "weighing something. She decides yes. She kisses you again. This one is\n"
                "different. This one is on purpose. Apollo, in your peripheral vision,\n"
                "stands up and sits down and stands up again and sits down again.\n\n"
                "She breaks off. 'Don't read too much into that, specialist.' She is\n"
                "reading too much into it. You can tell. Apollo is having a small\n"
                "private religious experience and Starbuck is pretending not to see it.",
                # beat 3
                "She does not kiss you this time. She looks at you for a long moment.\n"
                "Her eyes are doing something complicated, and so are her hands, and\n"
                "so is the air between you.\n\n"
                "'Listen, specialist,' she says. Her voice is quieter than you have\n"
                "ever heard it. 'You are a nice problem. You are not MY problem. I am\n"
                "the problem. I AM the problem. Go find a problem that doesn't already\n"
                "have a problem.'\n\n"
                "She squeezes your shoulder. It is, somehow, the worst part.",
            ],
            complicated_text=(
                "She looks up. She looks at you. She looks away. 'Specialist. We had a\n"
                "thing. We had a thing for like, an hour. Move on. I have.' She has not.\n"
                "But she has decided she has, which is, for Starbuck, the same thing."
            ),
        )

    if topic_lower in ("apollo", "captain", "lee"):
        return (
            "Her face does several things at once and lands on none of them. 'Apollo\n"
            "is a frakkin' boy scout. Apollo is a frakkin' marshmallow. Apollo is —\n"
            "you know what, Apollo is none of your frakkin' business, specialist.'\n"
            "She is not making eye contact. She is somehow making MORE than eye contact."
        )

    if topic_lower in ("six", "cylon", "blonde"):
        return (
            "'The new shift supervisor on deck twelve?' She grins. 'Hot. Suspicious.\n"
            "I'd hit it. I'd also shoot it. Same energy, different verb.'"
        )

    if topic_lower in ("self", "name"):
        return "'Starbuck. Pilot. Card sharp. Knuckle artist. Pleasure.'"

    return (
        "'I don't have time for the philosophical part of the conversation, specialist.\n"
        "Triad. Arm wrestling. Making out. PICK ONE.'"
    )


register_npc(NPC(
    id="starbuck",
    name="Lieutenant Thrace",
    aliases=["starbuck", "kara", "thrace", "lieutenant", "lt"],
    description=(
        "Kara Thrace, callsign Starbuck. Currently leaning back in a triad chair "
        "with her boots on the table, smoking, holding cards she is not looking at, "
        "and giving off the specific energy of a controlled explosion."
    ),
    on_talk=starbuck_on_talk,
))


# ─── Apollo ────────────────────────────────────────────────────────────────────


APOLLO_WRONG_MEMORIES = [
    "the launch tube",
    "the basestar incident",
    "the thing on Caprica",
    "the dinner at the Old Man's place",
    "the time with the chaplain",
    "what happened in the Raptor",
    "the morning after the second attack",
]


def _apollo_next_memory(world) -> str:
    state = world.npc_state.setdefault("apollo", {"memory_index": 0})
    idx = state["memory_index"]
    state["memory_index"] = idx + 1
    return APOLLO_WRONG_MEMORIES[idx % len(APOLLO_WRONG_MEMORIES)]


def apollo_on_talk(world, topic):
    bump_stat(world, "morale", 3)  # fraternizing
    if topic is None:
        memory = _apollo_next_memory(world)
        return (
            "Apollo turns. He looks at you. His eyes go wide. His face does a complete\n"
            "renovation in real time.\n\n"
            f"'Oh. Oh GODS. It's YOU. I — I've been wanting to talk to you about\n"
            f"{memory}. I haven't been able to think about anything else. I haven't —\n"
            "you have NO idea what I've been —'\n\n"
            "He stops. He looks at you closer. He squints.\n\n"
            "'... wait. Are you that specialist? From environmental?' His face does\n"
            "another renovation. This one is faster. 'Sorry. Sorry. You looked, in\n"
            "this light, exactly like someone I — never mind. What can I do for you,\n"
            "specialist?'"
        )

    topic_lower = topic.lower()

    if topic_lower in ("starbuck", "kara", "thrace"):
        return (
            "Apollo's whole face becomes a sigh. 'Kara. Kara is — Kara is — it's\n"
            "complicated. It's COMPLICATED. We — there's history. There's a lot\n"
            "of history. There's also a current. Also a future. We don't talk\n"
            "about it. We just sort of... circle. Like Vipers. Like wounded\n"
            "Vipers. Hot wounded Vipers.'\n\n"
            "He stares into the middle distance. He has forgotten you. The middle\n"
            "distance has not."
        )

    if topic_lower in ("six", "cylon", "supervisor", "blonde"):
        return (
            "His ears get very red, very fast. 'The — the new shift supervisor?\n"
            "I — I would not say I have NOTICED her. I would say she has come to my\n"
            "ATTENTION, which is — that is different. Specialist, do you think it's\n"
            "possible to be in love with three people at once?' He is not waiting\n"
            "for an answer. 'Asking for a... for a Viper friend.'"
        )

    if topic_lower in ("father", "adama", "dad"):
        return (
            "'My father is — my father is a great man. My father is also somebody\n"
            "I have been writing the same letter to for six years. I have never\n"
            "sent the letter. I have not finished the letter. I will finish it the\n"
            "week after I die in a Viper, probably.' He laughs. The laugh has\n"
            "tears in it."
        )

    if topic_lower in ("complicated",):
        return (
            "'IT IS complicated, specialist. I'm glad somebody finally said it. It's\n"
            "VERY complicated. Thank you. Thank you for getting it.'"
        )

    if topic_lower in ("self", "name", "apollo", "lee"):
        return (
            "'I'm — I'm Lee. Lee Adama. People call me Apollo. I prefer Lee. People\n"
            "still call me Apollo. I have made peace with this. Have I? I don't know.'"
        )

    # default — he keeps thinking the player is someone else
    return (
        f"'{_apollo_next_memory(world).capitalize()}? I — I don't want to talk\n"
        "about that here, specialist. Not here. Not now. Maybe later. Maybe never.\n"
        "Probably never.' He looks back out the porthole. He is gone."
    )


register_npc(NPC(
    id="apollo",
    name="Captain Apollo",
    aliases=["apollo", "lee", "captain", "lee adama"],
    description=(
        "Lee Adama, callsign Apollo. Square-jawed. Earnest. Currently staring out "
        "the porthole with the expression of a man trying to solve a quadratic "
        "equation made of feelings. He has the look of someone who has been "
        "rehearsing several emotionally honest conversations in his head, none of "
        "which he will ever actually have."
    ),
    on_talk=apollo_on_talk,
))


# ─── Dr. Baltar ────────────────────────────────────────────────────────────────


def _baltar_play_along(world):
    """Increment paranoia counter; bad outcome on continued engagement."""
    state = world.npc_state.setdefault("baltar", {"paranoia": 0, "co_conspirator": False})
    state["paranoia"] += 1
    state["co_conspirator"] = True
    world.flags["baltar_thinks_you_see_her"] = True
    bump_stat(world, "suspicion", 8)
    bump_stat(world, "cylon_vibes", 12)
    return (
        "Baltar's face lights up like a flare. He grabs you by both shoulders.\n\n"
        "'You can see her?! YOU CAN SEE HER!? OH thank the GODS. OH this changes —\n"
        "this changes EVERYTHING — I have so many questions — I — does she TALK to\n"
        "you too? Does she — wait. Wait. Don't tell HER you can see her. She'll —\n"
        "she's listening RIGHT NOW. Pretend you don't. Pretend HARD. We have to be\n"
        "STRATEGIC about this.'\n\n"
        "He releases you. He glances at the empty chair. He winks at the empty chair.\n"
        "He winks at you. He winks at the empty chair AGAIN.\n\n"
        "You have just become Baltar's co-conspirator. This is, on balance, bad."
    )


def _baltar_call_out(world):
    state = world.npc_state.setdefault("baltar", {"paranoia": 0, "co_conspirator": False})
    state["paranoia"] += 2
    world.flags["baltar_thinks_you_know"] = True
    bump_stat(world, "suspicion", 12)
    bump_stat(world, "morale", -3)
    return (
        "Baltar's face becomes a very calm, very horrible mask. He sets down the\n"
        "tablet. He approaches you with the specific bonhomie of a man who is about\n"
        "to do something irrevocable while still being charming.\n\n"
        "'There is NO ONE in the chair, specialist. There has NEVER been anyone in\n"
        "the chair. The chair has been EMPTY this ENTIRE conversation. I do not know\n"
        "WHAT you THINK you're seeing, but I would suggest, very strongly, that you\n"
        "consider whether the stress of your work has caught up with you. Have you\n"
        "considered seeing Doctor Cottle? I can RECOMMEND you. Personally. To Doctor\n"
        "Cottle. For an EXTENDED stay.'\n\n"
        "His smile does not move. Neither does the air. The empty chair is, you note,\n"
        "facing you now. Slightly. Even though nobody has moved it.\n\n"
        "You have just become Baltar's problem. This is, on balance, worse."
    )


def baltar_on_talk(world, topic):
    bump_stat(world, "morale", -2)  # he is exhausting
    # If you're "assisting Baltar" per the duty roster, talking to him counts.
    # The completion narrative is appended to whatever line he gives below.
    duty_extra = None
    if world.current_room == "baltars_lab":
        try:
            from content.duties import on_baltar_assist
            duty_extra = on_baltar_assist(world)
        except Exception:
            pass

    def _wrap(line: str) -> str:
        return line if not duty_extra else line + "\n\n" + duty_extra

    if topic is None:
        return _wrap(
            "Baltar startles, recovers, becomes very smooth. He had been mid-sentence\n"
            "with someone. There is no one there. He smiles. The smile is doing a lot\n"
            "of work.\n\n"
            "'Ah. Specialist. Yes. I was — I was running calculations. Out loud. As\n"
            "one does. It helps me think. What can I help you with? Has the President\n"
            "sent you? Don't answer that. Of course she hasn't. Why would she. Why\n"
            "would she send anyone. There's nothing to send anyone about.'\n\n"
            "Behind him, the empty chair appears to shift. It might be your eyes."
        )

    topic_lower = topic.lower()

    # The two "both bad" branches the user wants:
    if topic_lower in ("her", "she", "woman", "six", "vision", "the woman", "blonde"):
        return _baltar_play_along(world)
    if topic_lower in ("nobody", "no one", "alone", "yourself", "head", "imaginary", "empty chair", "chair"):
        return _baltar_call_out(world)

    if topic_lower in ("cylons", "cylon", "toasters"):
        return (
            "His left eye twitches. His right eye, separately, also twitches.\n"
            "'Cylons! Yes! A fascinating problem. I am the leading mind in Cylon\n"
            "detection in the Twelve Colonies, you know. Famously. The leading\n"
            "mind. There is nobody who would know more about Cylons than me. I am,\n"
            "in fact, the world expert. On Cylons. No conflict of interest there.\n"
            "No no no.'"
        )

    if topic_lower in ("project juno", "juno"):
        # Critical: this is the misdirection that distracts Baltar away from his
        # lab. Used by the wrench-quest take-guard.
        world.flags["baltar_distracted"] = True
        bump_stat(world, "suspicion", 3)
        return (
            "'WHAT.' Long pause. 'WHAT.' He laughs. The laugh is unattached to his\n"
            "face. 'Project Juno is a — that is a — that is CLASSIFIED, specialist.\n"
            "How — how do you EVEN — who TOLD you — wait. Wait. I need — I need to\n"
            "— excuse me. EXCUSE me.'\n\n"
            "He turns away. He paces. He paces FAST. He addresses the empty chair\n"
            "in a series of furious whispers. The lab, for the moment, has lost\n"
            "his attention entirely. The lab is, for the moment, unguarded."
        )

    if topic_lower in ("self", "name"):
        return (
            "'Doctor Gaius Baltar. Cylon expert. Public intellectual. Strongly\n"
            "single. Please don't tell anyone about the chair.'"
        )

    if topic_lower in ("president", "roslin"):
        return (
            "'Roslin? Roslin is a lovely woman. Lovely. WARM. Has she said anything\n"
            "about me? Has she mentioned my name? Has she — never mind. None of my\n"
            "business. Of course it isn't. I don't even know why I asked.'"
        )

    return (
        "He glances at the chair. He glances at you. He glances at the chair.\n"
        "'I'm sorry, what was the question? I lost the thread. Threads get lost.\n"
        "In here. Often. Why are you LOOKING at me like that. Stop LOOKING at me\n"
        "like that.'"
    )


register_npc(NPC(
    id="baltar",
    name="Doctor Baltar",
    aliases=["baltar", "doctor", "doctor baltar", "gaius", "scientist"],
    description=(
        "Doctor Gaius Baltar. Lab coat. Designer shirt under the lab coat. The "
        "lab coat is, you suspect, also designer. He is mid-conversation with "
        "an empty chair. He stops when he sees you, but only for a fraction of a "
        "second, and then he is smiling at you like an old friend who is also "
        "selling you something."
    ),
    on_talk=baltar_on_talk,
))


# ─── Number Six ────────────────────────────────────────────────────────────────


SIX_VIBE_THRESHOLD = 75


def _six_check_ending(world):
    if get_stat(world, "cylon_vibes") >= SIX_VIBE_THRESHOLD:
        return _six_cylon_love_triangle_ending(world)
    return None


def _six_cylon_love_triangle_ending(world) -> HandlerResult:
    return trigger_ending(
        world,
        "cylon_love_triangle",
        "She steps closer. The corridor smells like cinnamon and inevitability.\n"
        "She is about to say something. She doesn't.\n\n"
        "Around the corner steps... her. Again. Identical. Same red dress. Same hair.\n"
        "Same smile. Different vibe. The new one looks at you. She looks at the old\n"
        "one. They look at each other. The air goes electric.\n\n"
        "'You have GOT to be FRAKKIN' KIDDING me,' says the new one.\n\n"
        "'I saw him first,' says the old one. Calmly. Murderously.\n\n"
        "'You saw him SECOND,' says the new one.\n\n"
        "'I,' says the old one, 'saw him FIRST.'\n\n"
        "The new one looks at you. 'Specialist. With me. Now.' The old one grabs\n"
        "your other arm. 'No. With ME. Now.' You are being walked, by your two\n"
        "elbows, in two different directions, by two identical women, who hate each\n"
        f"other, who both like you.\n\n"
        f"'{world.player_name},' the new one says experimentally. 'Hmm. Yes. That works.'\n\n"
        "'I think,' says the old one, 'we are going to be very happy together. The\n"
        "three of us. The four of us. The thirteen of us. We will work it out.'\n\n"
        "Somewhere far away, you feel — distantly — the fleet jump. Without you.\n"
        "Adama will not notice. Tigh will not notice. You will not, when you think\n"
        "about it, mind.\n\n"
        "You are content. You are content in a way you have never been before. You\n"
        "are content in a way that the gods themselves would call concerning.\n\n"
        "── ENDING: CYLON LOVE TRIANGLE ──"
    )


SIX_REVEAL_HINTS = [
    "Her smile is patient in a way that suggests she has all the time in the universe. Which she might.",
    "She tilts her head. Then she tilts it again, slightly more, in a way that no human neck should do but humans never notice.",
    "You catch her reflection in the bulkhead. The reflection is half a second behind her. You stop looking at the bulkhead.",
    "Her eyes do that thing where they don't quite track. Then they correct, smoothly. Too smoothly.",
]


def six_on_talk(world, topic):
    # Check first — maybe a prior interaction already pushed us over.
    ending = _six_check_ending(world)
    if ending is not None:
        return ending

    # All Six interactions bump cylon_vibes; god/love/cylon bump harder.
    topic_lower = (topic or "").lower()
    if topic_lower in ("god", "gods", "faith", "love"):
        bump_stat(world, "cylon_vibes", 35)
    elif topic_lower in ("cylon", "toaster", "machine", "frakkin' toaster"):
        bump_stat(world, "cylon_vibes", 30)
    else:
        bump_stat(world, "cylon_vibes", 25)

    # Re-check after the bump; this is what triggers the ending on the talk that pushes you over.
    ending = _six_check_ending(world)
    if ending is not None:
        return ending

    cv = get_stat(world, "cylon_vibes")

    if topic is None:
        deja = ""
        if world.flags.get("ng_plus") and not world.npc_state.setdefault("six", {}).get("ng_plus_acknowledged"):
            world.npc_state["six"]["ng_plus_acknowledged"] = True
            deja = (
                "She is, somehow, smiling before you have arrived.\n\n"
                "'I knew you would come back. You always do. That's what we have, you\n"
                "and me. Iteration. Every time, you are closer to the version of\n"
                "yourself that finally — ' She lets the sentence end where it ended.\n"
                "The corridor goes on.\n\n"
            )
        hint_idx = max(0, (cv // 20) - 1)
        hint = SIX_REVEAL_HINTS[hint_idx % len(SIX_REVEAL_HINTS)] if cv >= 40 else ""
        text = deja + (
            "She turns to face you fully. The corridor narrows. The air does not\n"
            "exactly heat, but it becomes... attentive.\n\n"
            f"'{world.player_name}.' She says your name like she has been saying it\n"
            "for a long time. Maybe in another life. Maybe in a dream you don't\n"
            "remember. 'You came.'\n\n"
            "She did not give you her name. She does not need to. You both know."
        )
        if hint:
            text += "\n\n" + hint
        return text

    if topic_lower in ("self", "name"):
        return (
            "She smiles. The smile is too patient. 'You don't need my name,\n"
            "specialist. You haven't needed my name. You've always known.'"
        )

    if topic_lower in ("cylon", "toaster", "machine", "frakkin' toaster"):
        return (
            "She tilts her head. 'Is that what you think I am?' She does not look\n"
            "offended. She looks delighted. 'That would be... convenient, wouldn't\n"
            "it. To know.'"
        )

    if topic_lower in ("supervisor", "shift", "deck", "twelve"):
        return (
            "'I am your shift supervisor. I am also other things. The first is\n"
            "uncomplicated. The rest of it, you'll work out.'"
        )

    if topic_lower in ("baltar", "doctor"):
        return (
            "Her face does something complicated and brief, like a shadow under\n"
            "water. 'Gaius is... struggling. Gaius struggles. It is endearing.'"
        )

    if topic_lower in ("god", "gods", "faith", "love"):
        # Romance bump alongside the cylon_vibes spike that already happened above.
        # If this is their 3rd flirtation, the quadrangle fires here.
        return _romance_apply(
            world,
            "six",
            beat_texts=[
                "Her face becomes very still. Very lit. 'God is love, specialist.\n"
                "Love is everything. Everything is becoming. I think you and I are\n"
                "becoming.'",
                "She takes one step closer. The corridor narrows further.\n\n"
                "'I felt you reach for me just now. You don't know what for. I do.\n"
                "It will take time. It will take patience. It will take love.\n"
                "We have all three. Don't we, specialist.'\n\n"
                "It is not a question.",
                "She places a single fingertip on your sternum.\n\n"
                "'Soon,' she says. 'You will come with me. You will come willingly.\n"
                "I am patient with you because you are precious to me. You are mine.\n"
                "You have always been mine. You just hadn't met me yet.'\n\n"
                "Her finger stays where it is. The corridor stays where it is. You\n"
                "stay, mostly, where you are.",
            ],
            complicated_text=(
                "She smiles. The smile is patient. 'I will wait. I am exceptionally\n"
                "good at waiting. Find me when you are ready, specialist. I will\n"
                "still be becoming.'"
            ),
        )

    if topic_lower in ("apollo", "starbuck"):
        return (
            "She laughs. It is a small, kind laugh. 'They are children playing a\n"
            "game they invented. You and I are not children. Are we.'"
        )

    return (
        "She lets the question sit. She lets it sit for a long time. She does not\n"
        "answer it. She does not need to."
    )


register_npc(NPC(
    id="six",
    name="A Number Six",
    aliases=["six", "supervisor", "blonde", "woman", "her", "shift supervisor"],
    description=(
        "Tall. Blonde. Red. Wearing the deckhand coverall like it is, somehow, a "
        "red dress. She is either your shift supervisor, a Cylon agent, a "
        "hallucination from too many shifts, or all three. You cannot tell, and "
        "she will not tell, and that is somehow the most attractive part."
    ),
    on_talk=six_on_talk,
))


# ─── President Roslin ──────────────────────────────────────────────────────────


def roslin_on_talk(world, topic):
    world.flags["heard_roslin_prophecy"] = True
    bump_stat(world, "suspicion", 1)   # being seen with the President draws attention (small, doesn't compound brutally)
    bump_stat(world, "morale", 1)       # she's nice enough

    if topic is None:
        return (
            "President Roslin sets down the scriptures. She does not stand. She does\n"
            "not need to. She simply turns the full attention of someone with two\n"
            "months to live onto you.\n\n"
            "'Specialist. Come closer. Tell me, honestly: are you hiding a prophecy?'\n\n"
            "She is not joking. She is also not exactly serious. She is the third\n"
            "thing — the thing where it doesn't actually matter to her which one it\n"
            "is, because either way she has decided you might be useful."
        )

    topic_lower = topic.lower()

    if topic_lower in ("prophecy", "pythia", "scriptures", "religion", "faith"):
        # Opens the prophecy mini-quest by surfacing her vision.
        if not world.flags.get("quest_prophecy_started"):
            world.flags["quest_prophecy_started"] = True
            return (
                "She closes the scriptures around her thumb to hold the page.\n\n"
                "'Pythia is very specific, Specialist. A dying leader. A ragtag fleet.\n"
                "Twelve sources of guidance. And ONE young specialist of dubious\n"
                "provenance who shows up at the right moment with a small folded\n"
                "paper.\n\n"
                "I had a vision, Specialist. Yesterday. About you. SPECIFICALLY about\n"
                "you. I have not had a vision about a specialist before. There was\n"
                "a figure in a white robe. The figure was unimportant in itself, but\n"
                "the figure was holding the small folded paper.\n\n"
                "Were you the figure in the white robe? Be honest, please. Both\n"
                "answers are important. Both answers are also, possibly, wrong.'\n\n"
                "(You can answer: yes, no, or maybe.)"
            )
        if world.flags.get("quest_prophecy_resolved"):
            return (
                "'We had that conversation, Specialist. Whatever answer you gave was\n"
                "the wrong one. I'm at peace with it. The scriptures, on the other\n"
                "hand, are doing what they always do, which is nothing visible.'"
            )
        return (
            "'I am still waiting for your answer, Specialist. Yes, no, or maybe.\n"
            "I have very limited time. As I have, possibly, mentioned.'"
        )

    if topic_lower in ("yes", "yes the robe", "white robe", "robe", "i was"):
        if not world.flags.get("quest_prophecy_started"):
            return "Her eyebrows go up. 'Yes WHAT, Specialist. We have not begun a topic.'"
        if world.flags.get("quest_prophecy_resolved"):
            return "'We've had this conversation, Specialist.'"
        world.flags["quest_prophecy_resolved"] = True
        world.flags["quest_prophecy_choice"] = "yes"
        bump_stat(world, "suspicion", 12)
        return (
            "She nods, slowly. She is, you note, disappointed. She is, you note,\n"
            "trying not to show it.\n\n"
            "'Of course. Of course you were. That is exactly what the figure in\n"
            "the white robe would say. The figure in the white robe was, in the\n"
            "vision, a LIAR. The scriptures are very specific about this. I am,\n"
            "Specialist, very sorry to inform you that by saying yes, you have\n"
            "demonstrated that you were not the figure in the white robe.\n\n"
            "Or you were, and you ARE a liar. Both readings are correct.'\n\n"
            "She returns to her page. You can feel the bridge crew looking at you\n"
            "from three decks away, somehow."
        )

    if topic_lower in ("no", "not me", "wasn't me", "no the robe"):
        if not world.flags.get("quest_prophecy_started"):
            return "Her eyebrows go up. 'No WHAT, Specialist.'"
        if world.flags.get("quest_prophecy_resolved"):
            return "'We've had this conversation.'"
        world.flags["quest_prophecy_resolved"] = True
        world.flags["quest_prophecy_choice"] = "no"
        bump_stat(world, "morale", -5)
        return (
            "She nods, slowly. She is, you note, disappointed. She is, you note,\n"
            "trying not to show it.\n\n"
            "'Of course not. Of course it wasn't you. That is exactly what the\n"
            "figure in the white robe would say. The figure in the white robe\n"
            "denied being the figure in the white robe THROUGHOUT my vision. The\n"
            "scriptures are very clear that this is a hallmark of the figure. By\n"
            "denying it, you have, Specialist, very specifically demonstrated that\n"
            "you ARE the figure.\n\n"
            "Or you aren't. Both readings are correct.'\n\n"
            "She returns to her page. The page, you note, was the same page when\n"
            "you walked in. The page will be the same page when you leave."
        )

    if topic_lower in ("maybe", "i don't know", "dunno", "not sure", "unclear"):
        if not world.flags.get("quest_prophecy_started"):
            return "She tilts her head. 'Maybe WHAT, Specialist.'"
        if world.flags.get("quest_prophecy_resolved"):
            return "'We've had this conversation.'"
        world.flags["quest_prophecy_resolved"] = True
        world.flags["quest_prophecy_choice"] = "maybe"
        bump_stat(world, "suspicion", 8)
        bump_stat(world, "morale", -3)
        return (
            "She nods. 'Maybe. Of course. That is also what the figure in the white\n"
            "robe would say, because the figure in the white robe is, in the vision,\n"
            "EVASIVE. By being evasive, you have demonstrated that you ARE the\n"
            "figure. Or you aren't. Both readings are correct.'\n\n"
            "She returns to the page. The page, somehow, has aged."
        )

    if topic_lower in ("napkin", "paper", "folded paper", "numbers", "scrap"):
        if "napkin" in world.inventory:
            return (
                "Her eyes flick — just once — to your pocket. She does not look\n"
                "again. She does not need to. 'Sometimes a napkin is a napkin,\n"
                "Specialist. Sometimes a napkin is the napkin. Get it to the right\n"
                "hands.' She glances at the ceiling. 'I'm not saying whose. I'm not\n"
                "ALLOWED to say whose. The scriptures are clear that I'm not allowed\n"
                "to say whose. But the right hands belong to a man named after a\n"
                "river.' She nods. 'A long, slow river.'"
            )
        return "'I will know the napkin when I see it. The napkin will know me.'"

    if topic_lower in ("adama", "old man", "admiral", "bill"):
        return (
            "'The Admiral is a man of action. The Admiral does not believe in\n"
            "prophecy. The Admiral does, however, listen to me. Eventually.\n"
            "Eventually being the operative word.'"
        )

    if topic_lower in ("tigh", "colonel", "xo"):
        return (
            "Her mouth does a small, polite thing. 'The Colonel is — a man of —\n"
            "particular vintage. We do not, in the scriptures, contemplate the\n"
            "Colonel. The scriptures contemplate many things. The scriptures, in\n"
            "their wisdom, decline to contemplate the Colonel.'"
        )

    if topic_lower in ("baltar",):
        return (
            "Long, considering silence. 'I have very strong feelings about Doctor\n"
            "Baltar. They are not all polite. Some of them are theological. Some of\n"
            "them are political. ALL of them are correct.'"
        )

    if topic_lower in ("self", "name", "roslin", "president"):
        return (
            "'Laura Roslin. President of the Twelve Colonies. Schoolteacher. Dying.\n"
            "Pleased to meet you, Specialist.' She closes the scriptures with a\n"
            "small thud. 'Did I mention the dying part? The dying part is\n"
            "important.'"
        )

    if topic_lower in ("cylon", "cylons", "toasters"):
        return (
            "'There are Cylons on this ship. There are Cylons in this room. I am\n"
            "not paranoid, Specialist. I am ill. I am ill, and I am right, and the\n"
            "scriptures are clear.'"
        )

    return (
        "She does not answer. She watches you. She is waiting for the napkin.\n"
        "She has been waiting for the napkin all along."
    )


register_npc(NPC(
    id="roslin",
    name="President Roslin",
    aliases=["roslin", "president", "laura", "madam president"],
    description=(
        "Laura Roslin. The President. In a chair near the back of sickbay, "
        "reading the Sacred Scrolls of Pythia with the exact serene focus of "
        "someone who has been told she has two months to live and has decided to "
        "use them productively. There is a hospital robe over her shoulders. She "
        "is, somehow, still the most powerful person in the room."
    ),
    on_talk=roslin_on_talk,
))


# ─── Chief Tyrol ───────────────────────────────────────────────────────────────

TYROL_DEEP_GOSSIP = [
    "'Right. You got it. The XO and the Old Man have a STANDING APPOINTMENT in\n"
    "Adama's quarters. Tuesdays. THURSDAYS. Sometimes Fridays. Door locked. Glasses\n"
    "out. The XO comes out humming. THE XO DOES NOT HUM, SPECIALIST. The XO HUMMING\n"
    "is a frakkin' sign.'",

    "'Boomer? Yeah. She's been weird. She doesn't sleep. She SAYS she sleeps. But\n"
    "I clock her flying hours and her on-shift hours and there is no math that adds\n"
    "to sleep. Last week she asked me, very calmly, if I dream about water. I told\n"
    "her I dream about off-shift.'",

    "'Helo's back. You know that? Did you frakkin' KNOW that? He just walks in last\n"
    "week like he hadn't been on Caprica for half a frakkin' year. Smells like he\n"
    "hasn't slept in months. Asks me where Boomer is. I told him I don't know where\n"
    "Boomer is. I DO know where Boomer is. I'm not telling him.'",

    "'Apollo and Starbuck? Don't get me started. Don't. They have been having the\n"
    "same fight for SIX YEARS, specialist. SIX YEARS. They never resolve it. They\n"
    "never WILL resolve it. They are the engine of this ship. They will be having\n"
    "this fight when the Cylons board us. That'll be the last frakkin' sound.'",
]


def _tyrol_receive_algae(world):
    if "algae_bar" in world.inventory:
        world.inventory.remove("algae_bar")
    world.flags["tyrol_owes_gossip"] = True
    bump_stat(world, "morale", 3)
    return (
        "Tyrol's eyes track the algae bar like it's a sacred relic. He takes it\n"
        "between two grease-blackened fingers. He nods at you slowly, the way a\n"
        "priest might nod at a tithe.\n\n"
        "'Alright, specialist. You bought yourself some TIME. Ask me anything. Ask\n"
        "me ANYTHING. I've been awake for fourteen frakkin' hours and I know where\n"
        "the bodies are. Some of them metaphorical. Most of them not.'"
    )


def tyrol_on_talk(world, topic):
    state = world.npc_state.setdefault("tyrol", {"gossip_index": 0})
    bump_stat(world, "morale", 1)

    if topic is None:
        if world.flags.get("tyrol_owes_gossip"):
            idx = state["gossip_index"]
            state["gossip_index"] = idx + 1
            return TYROL_DEEP_GOSSIP[idx % len(TYROL_DEEP_GOSSIP)]
        return (
            "Tyrol is leaning on a Viper's wing with the exact posture of a man who\n"
            "has been awake since the second attack. He squints at you.\n\n"
            "'Specialist. What. Make it quick. I have a deck. The deck has problems.\n"
            "The problems have problems.'\n\n"
            "(He looks tired. He looks really tired. He looks the kind of tired that\n"
            "an algae bar might briefly redeem.)"
        )

    topic_lower = topic.lower()

    if topic_lower in ("boomer", "sharon", "valerii"):
        bump_stat(world, "cylon_vibes", 3)
        return (
            "Tyrol's face does something complicated. He tries to make it stop. It\n"
            "won't stop.\n\n"
            "'Boomer is a good pilot. Boomer is a great pilot. Boomer is — Boomer is\n"
            "— Boomer is something I'm not gonna talk about with a SPECIALIST, frak's\n"
            "sake. Move along.'\n\n"
            "He absolutely loves her. You can hear it. He hates that you can hear it."
        )

    if topic_lower in ("helo", "agathon"):
        return (
            "'Helo. Yeah. He's back. He's — listen. I'm happy he's alive. I'm THRILLED\n"
            "he's alive. I am ALSO going to be having some words with him about why\n"
            "he keeps asking me where my — where BOOMER is. Some words. Maybe a fight.\n"
            "Maybe a hug. We'll see how the day goes.'"
        )

    if topic_lower in ("tigh", "xo", "colonel"):
        return (
            "'The XO?' Tyrol exhales. 'Listen. I will not say anything against the XO\n"
            "while in uniform. I will not say anything against the XO while sober.\n"
            "I am, currently, both. So.' He shrugs. 'Some other time, specialist.'"
        )

    if topic_lower in ("dualla", "dee"):
        return (
            "'Dee? Good kid. Sharp. Too sharp for Apollo, frankly. Tell her I said hi.\n"
            "Actually don't. She'll know I'm telling people things. She doesn't like\n"
            "when I tell people things. Tell her nothing. Tell her I said nothing.'"
        )

    if topic_lower in ("gaeta", "felix"):
        return (
            "'Felix? Bridge officer. Knows everyone. Knows everyone's BUSINESS. Watch\n"
            "what you say in front of him. Watch what you say BEHIND him too. He has\n"
            "a list. Don't ask whose, you're on it.'"
        )

    if topic_lower in ("baltar", "doctor"):
        return (
            "'Don't get me started on him either, specialist. Last week he came down\n"
            "here and asked, in front of seven people, if my Raptors had souls. I told\n"
            "him my Raptors had a LOT of frakkin' things, and souls were the LEAST of\n"
            "them, and could he please get off my deck. He winked. AT THE EMPTY AIR.\n"
            "Then he left.'"
        )

    if topic_lower in ("self", "name"):
        return (
            "'Galen Tyrol. Deck chief. Twenty-two years in. I have not slept in nine\n"
            "of them. Pleasure, specialist.'"
        )

    if topic_lower in ("ship", "galactica"):
        return (
            "'She's a tough old girl. Held together by spit, prayer, and three\n"
            "specialists I trust including possibly you, if you're not the kind of\n"
            "specialist who asks questions like this.'"
        )

    if topic_lower in ("wrench", "missing wrench", "my wrench"):
        if world.flags.get("quest_wrench_complete"):
            return (
                "'You got my wrench back. I owe you. I will not, on this deck, in this\n"
                "uniform, express affection, specialist. But I'll buy you a drink off-\n"
                "shift if the gods grant us an off-shift. Which they won't. Move along.'"
            )
        return (
            "'My WRENCH, specialist. My FRAKKIN' wrench. PROPERTY OF G. TYROL, stamped\n"
            "three times on the handle. Missing for three days. I have a theory about\n"
            "where it is. The theory is BALTAR. The theory is BALTAR. I am NOT going\n"
            "to go down there myself because if I go down there myself I will commit a\n"
            "FRAKKIN' MURDER. So if you happen to be down there, and the wrench happens\n"
            "to be down there, and the wrench happens to come BACK with you, you and I\n"
            "are gonna be the best frakkin' friends this side of the Cyrannus system.'"
        )

    return (
        "Tyrol blinks slowly. 'I don't know. I'm tired. Ask me later. Ask me with\n"
        "snacks.'"
    )


def _tyrol_receive_wrench(world):
    if "wrench" in world.inventory:
        world.inventory.remove("wrench")
    world.flags["quest_wrench_complete"] = True
    bump_stat(world, "morale", 8)
    bump_stat(world, "suspicion", -10)  # the chief is a powerful ally
    return (
        "Tyrol takes the wrench between both grease-blackened hands like it's the\n"
        "first child he ever held. His face does something his face does not, on\n"
        "balance, have the structural integrity to do.\n\n"
        "'You. SPECIALIST. You did it. YOU FOUND HER.'\n\n"
        "He puts the wrench back in his belt with the slow ceremony of a man\n"
        "restoring a relic. He looks at you. He nods, exactly once.\n\n"
        "'Anyone gives you trouble on my deck, you come to me. Anyone gives you\n"
        "trouble OFF my deck, you ALSO come to me. We are gonna be the best frakkin'\n"
        "friends this side of the Cyrannus system. Now get OUT of my hangar.'\n\n"
        "(You note, in passing, that the service hatch in your bunk has been\n"
        "rattling at you for a while now. The wrench is, conveniently, no longer\n"
        "in your inventory. The wrench has, more conveniently, been used on the\n"
        "way out and the hatch is no longer your problem.)"
    )


register_npc(NPC(
    id="tyrol",
    name="Chief Tyrol",
    aliases=["tyrol", "chief", "galen"],
    description=(
        "Chief Galen Tyrol. Hangar deck chief. Looks like a man who has been awake "
        "since the gods made the rocks. Grease up to both elbows. A wrench in his "
        "belt, a wrench in his back pocket, and a wrench-shaped bruise on his "
        "forehead. He sees you. He has decided not to react to seeing you yet."
    ),
    on_talk=tyrol_on_talk,
    on_give={
        "algae_bar": _tyrol_receive_algae,
        "wrench": _tyrol_receive_wrench,
    },
))


# ─── Boomer ────────────────────────────────────────────────────────────────────

BOOMER_DREAM_PROMPTS = [
    ("water", "'Do you ever... dream about water? Just water. Going on forever. Going on so far it stops being water and starts being just BLUE.'"),
    ("home", "'Do you ever dream about home? Not Caprica. Not Galactica. A third place. A place you've never been but you know the layout.'"),
    ("the music", "'Do you ever wake up humming a song you don't know? Just four notes. Just four. Then they loop?'"),
    ("being someone else", "'Have you ever — and answer honestly — have you ever woken up and not been sure, just for a second, that you were you?'"),
]


def _boomer_prompt(world) -> tuple[str, str]:
    """Return (topic, prompt_text) for Boomer's current dream question."""
    state = world.npc_state.setdefault("boomer", {"prompt_index": 0})
    topic, text = BOOMER_DREAM_PROMPTS[state["prompt_index"] % len(BOOMER_DREAM_PROMPTS)]
    state["prompt_index"] += 1
    return topic, text


def boomer_on_talk(world, topic):
    bump_stat(world, "cylon_vibes", 2)  # she radiates the vibe

    if topic is None:
        _, prompt = _boomer_prompt(world)
        return (
            "Lieutenant Valerii — Boomer — turns to you. She has been staring at\n"
            "the wall. The wall, on inspection, is unremarkable. She looks at you\n"
            "with the specific intensity of a person who is checking whether you\n"
            "are real.\n\n"
            f"{prompt}\n\n"
            "(She is waiting for an answer. The Raptor behind her is also, somehow,\n"
            "waiting for an answer.)"
        )

    topic_lower = topic.lower()

    # Honest answers to her dream questions — these spike CYLON_VIBES.
    if topic_lower in ("water", "yes", "yes water", "ocean", "blue"):
        bump_stat(world, "cylon_vibes", 18)
        return (
            "Her eyes go very still. Her face does nothing. Then everything. Then\n"
            "nothing again.\n\n"
            "'Oh,' she says. Very softly. 'Oh, specialist. We should probably not\n"
            "talk about this here.'\n\n"
            "She looks around. The Raptor is still listening. The wall is still\n"
            "unremarkable. She does not move."
        )

    if topic_lower in ("home", "yes home", "third place"):
        bump_stat(world, "cylon_vibes", 18)
        return (
            "'You too,' she whispers. 'You TOO. The layout — it's a corridor and\n"
            "then it opens up and there are seven doors and the doors are all the\n"
            "same — please tell me you've seen the seven doors.'\n\n"
            "You did not say anything about seven doors. She is daring you to."
        )

    if topic_lower in ("the music", "music", "four notes", "song"):
        bump_stat(world, "cylon_vibes", 22)
        return (
            "She closes her eyes. She hums the four notes. They are the four notes.\n"
            "She knows they are. You know they are. The Raptor behind her is, in\n"
            "your peripheral vision, very still."
        )

    if topic_lower in ("being someone else", "yes someone else", "not me", "someone else"):
        bump_stat(world, "cylon_vibes", 25)
        return (
            "She takes your hand. Hers is warm. Hers is the right temperature for\n"
            "a human hand. You notice that. You notice that you noticed that.\n\n"
            "'It happens to me ALL the time, specialist. Every morning. Sometimes\n"
            "while I'm flying. Sometimes' — she looks down at her own hand on yours\n"
            "— 'while I'm awake.'\n\n"
            "She lets go. The temperature of the hangar does not return to what it\n"
            "was."
        )

    # Dismissive answers — no spike.
    if topic_lower in ("no", "nope", "nothing", "i don't", "dreams", "not really"):
        bump_stat(world, "morale", 1)
        return (
            "Her face closes. Like a door. Like a perfectly normal door, on a\n"
            "perfectly normal ship.\n\n"
            "'Right,' she says. 'Forget I asked, specialist. Forget I asked.' She\n"
            "turns back to the Raptor. She does not look at you again."
        )

    if topic_lower in ("helo", "agathon"):
        return (
            "Her face does seven different things in three seconds. She catches\n"
            "the seventh one. She holds it.\n\n"
            "'Karl is — Karl is back. I know. I haven't gone to him yet. I should\n"
            "go to him. I think — I think there's something I'm supposed to tell\n"
            "him. I can't remember what.'"
        )

    if topic_lower in ("tyrol", "chief", "galen"):
        return (
            "Her face softens in a way that has nothing to do with Tyrol being on\n"
            "the bridge, four decks, and one frakkin' war away. 'Galen is — Galen\n"
            "is wonderful. Galen is good. I don't deserve Galen. I am, possibly,\n"
            "going to ruin Galen's life. I hope not.'\n\n"
            "She smiles. The smile does not reach her eyes. The eyes are doing\n"
            "their own thing."
        )

    if topic_lower in ("cylon", "cylons", "toaster"):
        bump_stat(world, "cylon_vibes", 10)
        return (
            "She laughs. The laugh is one note too short. 'A specialist asking a\n"
            "pilot about toasters. What a frakkin' world.'\n\n"
            "She does not answer your question. You did not, technically, ask one."
        )

    if topic_lower in ("self", "name"):
        return (
            "'Sharon Valerii. Callsign Boomer. Raptor jock. Twelve years sober.\n"
            "Almost twelve.' She blinks. 'Sober from drinking. Sober from other\n"
            "things, I don't know. Some of them I don't know I'm doing.'"
        )

    return (
        "She doesn't answer. She is somewhere else for a second. Then she's back.\n"
        "She does not seem to notice the gap."
    )


register_npc(NPC(
    id="boomer",
    name="Lieutenant Valerii",
    aliases=["boomer", "sharon", "valerii", "lieutenant valerii"],
    description=(
        "Sharon 'Boomer' Valerii. Raptor pilot. Standing very still next to her "
        "Raptor, looking at a wall. The wall is not doing anything. She has been "
        "looking at it for the better part of an hour. When she notices you, her "
        "face takes one extra beat before it remembers how to do the friendly thing."
    ),
    on_talk=boomer_on_talk,
))


# ─── Helo ──────────────────────────────────────────────────────────────────────

HELO_DEFAULT_BEATS = [
    # beat 1 — first encounter, mistakes player for Sharon
    "He looks up. He sees you. His whole face does something his face does not, on\n"
    "balance, have the structural integrity to do.\n\n"
    f"'Oh GODS. It's been so long.' He stands up fast. He is taller than you remembered.\n"
    "He's taller than you have ever remembered, because you have never met him. He\n"
    "stops himself a foot short of you and stares.\n\n"
    "'Wait. Wait. You're not — sorry. Sorry. You have her exact eyes. You have HER\n"
    "EXACT EYES, specialist. I'm so sorry. Tell me everything. About yourself. Tell\n"
    "me. Are you from Aerilon? You look like you're from Aerilon. SHE was from\n"
    "Aerilon.'",
    # beat 2
    "He sees you. He LIGHTS up. Then he REMEMBERS. The lighting up and the remembering\n"
    "happen so close together that they are functionally the same expression.\n\n"
    "'Specialist. Specialist. Hi.' He is sitting on a sickbay bed. He has not been\n"
    "discharged. He may never be discharged. 'Did you ever go back to Caprica? We — I —\n"
    "Sharon and I — there was a CITY. There was a SHOWER. I can't talk about it. I'm\n"
    "talking about it. I'm so sorry. You have her exact eyes.'",
    # beat 3
    "He stands up. He sits down. He stands up again. His jaw works. His eyes are doing\n"
    "the soulful thing. The soulful thing is doing some heavy lifting.\n\n"
    "'Listen. I know it's fast. I know I am, technically, not currently — listen.\n"
    "Will you have dinner with me. Mess hall. Tonight. Just — bring whatever Sharon\n"
    "you've got inside you. Bring all of it. I'll bring the rest.'",
]


HELO_COMPLICATED = (
    "He sees you. He looks at you for a long time. His shoulders relax. Something\n"
    "in him resolves.\n\n"
    "'Specialist. I — I'm going to need some time. Some space. Some specialist of\n"
    "a different shape, frankly. I'm sorry. You were — you are a kind person. You\n"
    "are not the right person. I'm going to go find Boomer now. I should have done\n"
    "that an hour ago.'"
)


def helo_on_talk(world, topic):
    bump_stat(world, "morale", 2)  # he's earnest, it's nice

    if topic is None:
        return _romance_apply(world, "helo", HELO_DEFAULT_BEATS, HELO_COMPLICATED)

    topic_lower = topic.lower()

    if topic_lower in ("sharon", "boomer", "valerii"):
        return (
            "He folds. His face does the thing where it tries to be brave and the\n"
            "trying is itself the heartbreak.\n\n"
            "'Sharon was — Sharon IS — listen. There were two Sharons. Or one Sharon\n"
            "twice. Or the same Sharon, but — I don't have the words. I haven't\n"
            "had the words in eight months. I'm working on them.'"
        )

    if topic_lower in ("caprica", "city"):
        return (
            "'Caprica was — Caprica was a CITY. We hid. We ate. We made plans. We\n"
            "made — listen. I am NOT going to make you sit through the entire\n"
            "Caprica story, specialist. (Pause. He is going to make you sit through\n"
            "the entire Caprica story.) Caprica was —'\n\n"
            "(You decide, quietly, that you do not have time for the entire Caprica\n"
            "story today. You make a polite face. He continues for another ten\n"
            "minutes. You nod. You nod some more. You nod with your eyes.)"
        )

    if topic_lower in ("tyrol", "chief", "galen"):
        return (
            "His expression goes complicated and stays there. 'Tyrol is a good man.\n"
            "Tyrol is a GOOD man. Tyrol is also — listen. Boomer and Tyrol have a\n"
            "thing, allegedly, and I am NOT going to be the guy who shows up after\n"
            "eight months and ruins it. I am also possibly going to be that guy. I\n"
            "haven't decided.'"
        )

    if topic_lower in ("self", "name"):
        return (
            "'Karl Agathon. Callsign Helo. I've been on Caprica for eight months. I\n"
            "have been back for one week. The week has been longer than the eight\n"
            "months in some respects. Pleasure, specialist.'"
        )

    if topic_lower in ("cottle", "doc", "doctor"):
        return (
            "He laughs. 'Cottle is a frakkin' national treasure. He told me, on\n"
            "intake, that I looked like hell. Which is fair. I do.'"
        )

    return (
        "He looks at you with such complete sincerity that you, briefly, forget\n"
        "what you were going to ask him. He waits, patient, while you remember.\n"
        "You don't remember. He pats your shoulder. You go on with your day."
    )


register_npc(NPC(
    id="helo",
    name="Captain Agathon",
    aliases=["helo", "karl", "agathon", "captain agathon"],
    description=(
        "Captain Karl 'Helo' Agathon. Just back from Caprica after a frankly "
        "miraculous eight months. Sitting on a sickbay bed in his off-duty fatigues. "
        "His eyes look like they've seen things and the things were mostly named "
        "Sharon. He is the kind of earnest that is technically a load-bearing "
        "personality trait."
    ),
    on_talk=helo_on_talk,
))


# ─── Lieutenant Gaeta ──────────────────────────────────────────────────────────


def gaeta_on_talk(world, topic):
    # Gaeta is the OFFICER who remembers your name. He breaks the contract.
    state = world.npc_state.setdefault("gaeta", {"opinion_index": 0})
    bump_stat(world, "morale", 2)

    if topic is None:
        name = world.player_name
        return (
            f"Lieutenant Gaeta looks up from his console. He looks at you. He says,\n"
            f"without hesitation, your name.\n\n"
            f"'Specialist {name}. Right? I keep a list. Don't ask why.'\n\n"
            f"He smiles a small, weary, watching-the-Empire-fall smile. 'Welcome to\n"
            f"CIC. You shouldn't be here. I'm choosing not to notice. What can I\n"
            f"help you with.'"
        )

    topic_lower = topic.lower()

    if topic_lower in ("list", "the list"):
        return (
            "'The list is everyone the XO has yelled at, threatened with the brig,\n"
            "or paged on the intercom in the wrong tone of voice in the past month.\n"
            "You are on the list. You are, in fact, ALPHABETIZED on the list. There\n"
            f"is a sub-list for specialists. You are on the sub-list as \"{world.player_name},\n"
            "Specialist, Toilet Drama Day,\" which I think is overspecific but I\n"
            "didn't write that one.'"
        )

    if topic_lower in ("dualla", "dee"):
        return (
            "'Dee mentioned you. She had opinions.' He pauses. 'You should ask her.\n"
            "I want to hear what she tells you. I have a bet running with myself.'"
        )

    if topic_lower in ("adama", "old man", "admiral"):
        return (
            "Gaeta exhales. 'The Old Man is the Old Man. He plays cards, he drinks,\n"
            "he stares meaningfully, he wins. He is undefeated at meaningful staring\n"
            "in this fleet. He is undefeated at HEAVYWEIGHT meaningful staring. Don't\n"
            "challenge him.'"
        )

    if topic_lower in ("tigh", "xo", "colonel"):
        return (
            "Gaeta's face does a complicated wince. 'The XO is a tragedy with a flask\n"
            "in it. I love him. I want him spaced. Both at once. I think he would\n"
            "respect that.'"
        )

    if topic_lower in ("baltar", "doctor"):
        bump_stat(world, "suspicion", 2)
        return (
            "'Don't even START with Baltar. He came up here last week and asked, very\n"
            "calmly, if I \"felt watched.\" I am ALWAYS watched, Doctor. I am ON THE\n"
            "BRIDGE. I am ON CAMERA. I am, currently, on FOUR cameras. Get OUT of\n"
            "CIC.'"
        )

    if topic_lower in ("starbuck", "thrace", "kara"):
        return (
            "'Thrace is a thunderstorm with sidearms. I have a soft spot for her. I\n"
            "would never tell her that. She would weaponize it inside an hour.'"
        )

    if topic_lower in ("apollo", "lee"):
        return (
            "'Apollo is — Apollo is a fine pilot. Apollo is a fine son. Apollo is\n"
            "going to die holding hands with someone he hasn't told he loves them.\n"
            "Probably Starbuck. Possibly Dee. Possibly both.'"
        )

    if topic_lower in ("jump", "ftl", "coordinates", "coords"):
        world.flags["heard_adama_jump_prep"] = True
        return (
            "He glances at the plot. 'We're jumping. We don't know when. The XO has\n"
            "the coordinates. The XO is in the head. I have inferences. I do not have\n"
            "coordinates. If you, hypothetically, found coordinates on, hypothetically,\n"
            "a frakkin' NAPKIN, I would, hypothetically, find that a normal Tuesday.'"
        )

    if topic_lower in ("self", "name"):
        return (
            "'Lieutenant Felix Gaeta. Bridge officer. I sit here. I press buttons. I\n"
            "keep lists. I am, on balance, fine. I think.'"
        )

    if topic_lower in ("cylons", "cylon"):
        return (
            "Gaeta's voice drops. 'There are Cylons in this fleet. I am not going to\n"
            "name names. I am going to say that I run the duty rosters and three of\n"
            "them, last month, did not match the personnel manifests. I corrected the\n"
            "discrepancy. I corrected it BOTH WAYS. I did not, technically, sleep that\n"
            "night.'"
        )

    return (
        "Gaeta tilts his head. 'I don't have an opinion on that one. Yet.' He\n"
        "writes something on a sticky note and puts it on his console."
    )


register_npc(NPC(
    id="gaeta",
    name="Lieutenant Gaeta",
    aliases=["gaeta", "felix", "lt gaeta", "lieutenant gaeta"],
    description=(
        "Lieutenant Felix Gaeta. CIC bridge officer. Standing at the secondary plot "
        "with the specific posture of a man who has been the only competent person "
        "in the room for several hours. He looks tired. He looks observant. He looks "
        "like he is keeping notes. He is, in fact, keeping notes."
    ),
    on_talk=gaeta_on_talk,
))


# ─── Doc Cottle ────────────────────────────────────────────────────────────────

COTTLE_PREFIX = "Cottle takes a long drag. He blows smoke at the ceiling fan, which has long since stopped trying. "


def cottle_on_talk(world, topic):
    bump_stat(world, "morale", 1)

    # Hidden Cylon mechanic: Cottle, with the only working blood lab on the
    # ship, notices something he can't quite name. Fires once when the player
    # is Cylon. He won't elaborate. He won't go on the record. He smokes.
    if world.flags.get("is_cylon") and not world.flags.get("cottle_bloodwork_warned"):
        world.flags["cottle_bloodwork_warned"] = True
        return (
            COTTLE_PREFIX +
            "He squints. He squints HARDER. He flips a clipboard you hadn't seen\n"
            "him pick up.\n\n"
            "'Your bloodwork is... huh.'\n\n"
            "Long pause. He blows smoke at the ceiling. The ceiling, in solidarity,\n"
            "blows nothing back.\n\n"
            "'Forget I said anything, kid. Don't come back. Come back if you start\n"
            "hummin' a tune you don't remember learning. Otherwise — forget I said\n"
            "anything.'\n\n"
            "He does not, you note, blink for the rest of the conversation. Cottle\n"
            "blinks. Cottle is not, currently, blinking."
        )

    if topic is None:
        if not world.flags.get("cottle_offered_cigarette"):
            world.flags["cottle_offered_cigarette"] = True
            return (
                COTTLE_PREFIX +
                "He squints at you.\n\n"
                "'You look like hell, kid. Not unusual for one of you specialists.\n"
                "Notable, even on you.' He digs in a coat pocket. 'You want a cigarette?\n"
                "I've got a frakkin' supply. Don't ask. Ask Cottle for a cigarette,\n"
                "you get a cigarette. That's the rule. Ask Cottle for advice, you get\n"
                "advice. Don't ask Cottle for advice. The advice is bad.'"
            )
        return (
            COTTLE_PREFIX +
            "'Still here, kid? Good. Means you're not dead. Means I'm not currently\n"
            "yelling at someone over you. We call that a Tuesday.'"
        )

    topic_lower = topic.lower()

    if topic_lower in ("cigarette", "cigarettes", "smoke"):
        if "cigarette" not in world.inventory and not world.flags.get("got_cigarette"):
            world.flags["got_cigarette"] = True
            move_item_to_inventory(world, "cigarette")
            return (
                COTTLE_PREFIX +
                "'Knock yourself out, kid.' He hands you a slightly-bent cigarette\n"
                "and a book of matches with the Galactica seal on it. 'Don't light it\n"
                "in here. Or do. I'm not your mother. Your mother smoked. Statistically\n"
                "everybody's mother smoked.'"
            )
        return (
            COTTLE_PREFIX +
            "'Already gave you one, kid. Make it last.'"
        )

    if topic_lower in ("advice", "bad advice"):
        return (
            COTTLE_PREFIX +
            "'Bad advice? Here's three.\n\n"
            "  One: do not date pilots. Do not date pilots even if the pilot is hot.\n"
            "    Especially if the pilot is hot.\n\n"
            "  Two: if the XO offers you something to drink, the answer is no. I do\n"
            "    not care what it is. I do not care if it is in a CANTEEN. The\n"
            "    answer is no, kid.\n\n"
            "  Three: nobody is okay. NOBODY. If somebody says they're okay, they\n"
            "    are about to die or about to confess something. There is no third\n"
            "    option.'"
        )

    if topic_lower in ("tigh", "xo", "colonel"):
        return (
            COTTLE_PREFIX +
            "'Tigh? Listen, kid. If the XO ever asks you to fill a canteen, you say\n"
            "no. You say frakkin' NO. You hear me? You will live longer. I won't\n"
            "have to fish you out of a vent. I have done it before. I would prefer\n"
            "not to do it again.'"
        )

    if topic_lower in ("roslin", "president"):
        return (
            COTTLE_PREFIX +
            "His face softens. He doesn't allow it for long. 'She's a tough woman.\n"
            "Tougher than the diagnosis. Tougher than the office. Don't ever tell\n"
            "her I said that, kid. Don't even tell her I have feelings. The feelings\n"
            "are a violation of regs.'"
        )

    if topic_lower in ("helo",):
        return (
            COTTLE_PREFIX +
            "'Agathon? Stable. Underweight. Skin in three colors. Looks like a man\n"
            "who has seen the gods and didn't like them. I'm keeping him here for\n"
            "two more days. Three if I think Boomer will visit. Boomer won't visit.\n"
            "She'll come to the door and stand outside and leave.'"
        )

    if topic_lower in ("boomer", "sharon"):
        return (
            COTTLE_PREFIX +
            "His eyes narrow. 'Valerii is — Valerii is on my list. I run scans on\n"
            "every pilot. Hers come back funny. They come back HUMAN, kid. But the\n"
            "spreadsheet has a tone. I am tired of the spreadsheet's tone.'"
        )

    if topic_lower in ("self", "name", "cottle"):
        return (
            COTTLE_PREFIX +
            "'Major Sherman Cottle. Chief medical officer. I smoke. I drink. I am,\n"
            "as a result, the healthiest person on this frakkin' ship. Make your\n"
            "peace with that, kid.'"
        )

    if topic_lower in ("sleep", "rest", "tired", "exhaustion", "exhausted"):
        return (
            COTTLE_PREFIX +
            "'Sleep advances time, kid. The watch clock keeps turning. You hit your\n"
            "rack and you wake up at the next watch — Morning, Forenoon, Afternoon,\n"
            "whatever was queued up. SLEEP is the time-skip. It is also, separately,\n"
            "good for you. Make of that what you will.'"
        )

    if topic_lower in ("napkin", "paper"):
        return (
            COTTLE_PREFIX +
            "'A napkin? With NUMBERS? Kid, I am a doctor, not a frakkin' cryptographer.\n"
            "Take it to the bridge. Take it to a math person. Don't take it to me. I\n"
            "will set it on fire and use it to light my next cigarette.'"
        )

    return (
        COTTLE_PREFIX +
        "'I don't know, kid. Ask somebody who hasn't been awake since the second\n"
        "attack. There aren't many. Try Gaeta. Gaeta knows everything. Gaeta is also\n"
        "going to die of caffeine. Make your choices.'"
    )


register_npc(NPC(
    id="cottle",
    name="Doctor Cottle",
    aliases=["cottle", "doc", "doctor cottle", "major cottle"],
    description=(
        "Doctor Sherman Cottle. Chief medical officer. Mid-cigarette. Scrubs blue. "
        "Teeth not. The cigarette is, by your count, his third in twenty minutes. "
        "The cigarette is wedged in the corner of his mouth in a way that suggests "
        "the cigarette is structural. He looks at you with the specific patience of "
        "a man who has heard every excuse and is not, in any way, in the market for "
        "a new one."
    ),
    on_talk=cottle_on_talk,
))


# ─── Dualla ────────────────────────────────────────────────────────────────────

DUALLA_DEFAULT = (
    "Petty Officer Dualla looks up from her console. She looks at you. She looks at\n"
    "you for a beat longer than is professional. Then she looks back at her console.\n\n"
    "'Specialist.' Her voice is flat. Her voice is fond. The two facts coexist.\n"
    "'I've heard your name. From Gaeta. He has a list. You're on it. Don't ask why.\n"
    "I'm not the one to tell you. (I might be the one to tell you. I'll think about\n"
    "it.)'"
)

DUALLA_BEATS = [
    # beat 1 — about apollo
    "She does not look up. 'Apollo's a lovely man. Apollo's a stupid man. The two\n"
    "facts coexist. They are sometimes the same fact.' Now she looks up. 'I'm\n"
    "settling, specialist. I want you to know that. I am SETTLING. There. I said\n"
    "it. Out loud. To a SPECIALIST. The bridge is going to be insufferable about\n"
    "this for weeks.'",
    # beat 2 — hypothetically
    "Her voice goes very even. 'If you HAD to choose between an officer who is\n"
    "technically your job and an enlisted who is technically a person, who would\n"
    "you choose. Hypothetically.' She does not look up. She does not blink. The\n"
    "headset wire on her neck is, you note, very straight.\n\n"
    "(She is waiting for a specific kind of answer. You are not entirely sure which\n"
    "one. You give the one that feels right. It feels right because she nods.)",
    # beat 3 — what's your shift like
    "'Specialist. What's your shift like.' She is still not looking up. 'Hypothetically.\n"
    "Like, what are your hours. Do you have time. Do you have, specifically, time.\n"
    "Asking for a friend. The friend is me. I am asking for me.'\n\n"
    "(Apollo enters CIC at the far end. He waves. He has no idea what is happening.\n"
    "Dee does not wave back. The wave dies on the air between you.)",
]

DUALLA_COMPLICATED = (
    "She looks up. She looks at you. She looks at Apollo, across CIC. She looks at\n"
    "you again.\n\n"
    "'I think I've made my decision about Apollo. And it is not — it is not, in\n"
    "fact, you, specialist. I'm sorry. You seem nice. You'll be fine. I'll be fine.\n"
    "Apollo will be — Apollo will be Apollo.' She puts her headset back on. The\n"
    "conversation is over."
)


def dualla_on_talk(world, topic):
    bump_stat(world, "morale", 1)

    if topic is None:
        return DUALLA_DEFAULT

    topic_lower = topic.lower()

    # Romance-bumping flirty topics
    if topic_lower in ("apollo", "lee"):
        return _romance_apply(world, "dualla", DUALLA_BEATS, DUALLA_COMPLICATED)
    if topic_lower in ("self", "name", "you", "yourself"):
        return _romance_apply(world, "dualla", DUALLA_BEATS, DUALLA_COMPLICATED)
    if topic_lower in ("hypothetically", "shift", "time"):
        return _romance_apply(world, "dualla", DUALLA_BEATS, DUALLA_COMPLICATED)

    # Non-flirty judgment topics
    if topic_lower in ("starbuck", "thrace", "kara"):
        return (
            "'Thrace is exhausting. Thrace is necessary. Thrace is somebody else's\n"
            "problem. I have made my peace with the fact that Thrace is not, in any\n"
            "meaningful sense, going to allow herself to be a problem I can solve.\n"
            "Specialists may, of course, draw their own conclusions about what that\n"
            "implies.' She is implying something specific. You catch about half of it."
        )

    if topic_lower in ("tigh", "xo", "colonel"):
        return (
            "'I will not comment on the XO. I have NOT been instructed to NOT\n"
            "comment. I am choosing not to. There is a difference. I want you to\n"
            "know there is a difference, specialist.'"
        )

    if topic_lower in ("adama", "admiral", "old man"):
        return (
            "'The Admiral is the Admiral. He is, in his way, exactly correct. In\n"
            "another way, he is also Apollo's father, which is a different problem\n"
            "for me, but a problem.'"
        )

    if topic_lower in ("gaeta", "felix"):
        return (
            "'Felix is — Felix is the only person on this bridge who I can have a\n"
            "conversation with that doesn't make me want to short out the comms\n"
            "panel. That is more love than you might assume.'"
        )

    if topic_lower in ("baltar", "doctor"):
        return (
            "Her face does nothing. Her face is doing the most by doing nothing.\n"
            "'Doctor Baltar is, when he comes up here, asked very politely to leave.\n"
            "Sometimes, on my off-shifts, I imagine asking him less politely. It is\n"
            "a small joy. It is one of the small joys I am allowed.'"
        )

    if topic_lower in ("helo", "agathon"):
        return (
            "'Captain Agathon is back. We knew, two days before anyone told us, that\n"
            "he was back. Comms knew. Comms knows everything. Comms is, in many ways,\n"
            "the conscience of this ship. We do not have ENOUGH conscience for this\n"
            "ship.'"
        )

    if topic_lower in ("boomer", "valerii"):
        bump_stat(world, "cylon_vibes", 4)
        return (
            "Her voice drops. 'I run the comms for every Raptor in the air. Boomer's\n"
            "Raptor sometimes — sometimes calls in coordinates that don't exist.\n"
            "Sometimes I think she doesn't know she's done it. I have not, formally,\n"
            "reported this. I am, informally, reporting it to a specialist. Make of\n"
            "that what you will.'"
        )

    return (
        "She does not answer. She is judging. The judging is, in its way, the answer."
    )


# ─── Cook (Mystery Meat) ──────────────────────────────────────────────────────


def cook_on_talk(world, topic):
    bump_stat(world, "morale", -1)

    if topic is None:
        return (
            "The cook does not turn around. The cook is stirring a vat. The vat has\n"
            "been being stirred for as long as you can remember being a person.\n\n"
            "'Whaddaya want, specialist. Move it along. Line's gonna form. Line's\n"
            "ALWAYS gonna form.'"
        )

    t = topic.lower()

    if t in ("meat", "protein", "mystery meat", "lasagna", "vat"):
        bump_stat(world, "suspicion", 3)
        return (
            "The cook stops stirring. The cook turns around. The cook is wearing an\n"
            "apron that has been an apron since the second war.\n\n"
            "'Specialist. We are NOT going to talk about the meat. We are NOT going\n"
            "to talk about the protein. We are NOT going to talk about the lasagna.\n"
            "We are CERTAINLY not going to talk about the VAT. The vat is fine. The\n"
            "vat has always BEEN fine. Now get OUT of my kitchen.'\n\n"
            "The cook is shaking very slightly. The cook turns back to the vat. The\n"
            "cook resumes stirring."
        )

    if t in ("engram", "crewman engram", "rat", "skeleton"):
        bump_stat(world, "suspicion", 5)
        return (
            "The cook stops dead. The cook does not turn around. The cook's voice\n"
            "is suddenly very flat.\n\n"
            "'I don't know what you're talkin' about, specialist. I don't know any\n"
            "Engram. I don't know any rats. I don't know what's in the vat. The vat\n"
            "knows what's in the vat. Don't ASK the vat. Don't ASK ME.'\n\n"
            "The cook is now stirring the vat very fast."
        )

    if t in ("tigh", "xo", "colonel"):
        return (
            "'The XO?' The cook laughs. The laugh has nothing in it. 'The XO has not\n"
            "eaten a lasagna in nineteen years, specialist. The XO knows what's in\n"
            "the lasagna. The XO is, possibly, the only person on this ship besides\n"
            "me who knows what's in the lasagna. We have an UNDERSTANDING.'"
        )

    if t in ("algae", "algae bar", "bar"):
        return (
            "'Algae bars are FINE, specialist. The bars are NOT the lasagna. The\n"
            "bars are PROCESSED. The lasagna is what's LEFT.'\n\n"
            "The cook says 'left' in a way that is upsetting."
        )

    if t in ("self", "name"):
        return (
            "The cook waves a ladle at you. 'I cook. That's what I do. Names are\n"
            "for people whose VATS are not the SOURCE OF THEIR WHOLE FRAKKIN'\n"
            "IDENTITY. Move it along.'"
        )

    if t in ("hadrian", "specialist hadrian", "crewman"):
        return (
            "'Hadrian eats two trays of lasagna a day, specialist. TWO. He has\n"
            "asked me three times what's in it. I have told him three times that\n"
            "he doesn't want to know. He keeps eating it. Frakkin' machine.'"
        )

    if t in ("hours", "schedule", "open", "closed", "mess hours"):
        return (
            "'Morning. Afternoon. THAT'S IT. Don't come around at Dog Watch askin'\n"
            "for a tray, specialist. The kitchen is CLOSED. The VAT keeps stirring\n"
            "regardless — vat doesn't care about your shift. But the line is shut\n"
            "and I am ELSEWHERE. Got me?'"
        )

    return (
        "The cook does not respond. The cook stirs. The vat receives a single\n"
        "additional unidentified contribution from a place you cannot see."
    )


register_npc(NPC(
    id="cook",
    name="The Cook",
    aliases=["cook", "the cook", "chef"],
    description=(
        "An indeterminate person in a stained apron, stirring a vat that has been "
        "stirred for the duration of the war. The cook does not, as a matter of "
        "policy, make eye contact with anyone who has not personally contributed "
        "to the vat."
    ),
    on_talk=cook_on_talk,
))


register_npc(NPC(
    id="dualla",
    name="Petty Officer Dualla",
    aliases=["dualla", "dee", "petty officer dualla", "anastasia"],
    description=(
        "Petty Officer Anastasia Dualla. Communications. Standing at the comms console "
        "with the specific posture of a person who has been judging absolutely "
        "everybody for the last twelve hours and is not, currently, in the mood to "
        "stop. She has her headset on one ear. The other ear is, you suspect, "
        "monitoring everything within twenty meters."
    ),
    on_talk=dualla_on_talk,
))
