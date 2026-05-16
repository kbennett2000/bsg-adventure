"""All NPCs for the full game."""

from engine.commands import HandlerResult, trigger_ending
from engine.models import NPC
from engine.registry import register_npc
from engine.world import move_item_to_inventory, move_item_to_room


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

# Topics that, asked of Tigh, raise his suspicion that the player knows something
# they shouldn't. At 3+, he spaces them.
TIGH_DANGER_TOPICS = {"flask", "water", "adama", "bill", "commander", "meeting", "meetings", "quarters"}


def _tigh_next_wrong_name(world) -> str:
    state = world.npc_state.setdefault("tigh", {})
    idx = state.get("wrong_name_index", 0)
    state["wrong_name_index"] = idx + 1
    return TIGH_WRONG_NAMES[idx % len(TIGH_WRONG_NAMES)]


def _tigh_bump_suspicion(world, amount: int = 1) -> int:
    state = world.npc_state.setdefault("tigh", {})
    new = state.get("suspicion", 0) + amount
    state["suspicion"] = new
    return new


def _tigh_should_space(world) -> bool:
    return world.npc_state.get("tigh", {}).get("suspicion", 0) >= 3


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


def _tigh_give_quest(world):
    # Once Tigh's suspicion is high, the next default talk triggers the spaced ending.
    if _tigh_should_space(world):
        return _tigh_spaced_ending(world)
    if world.flags.get("got_canteen"):
        return (
            "Tigh squints at you through the stall slats. 'You still here, specialist? "
            "ENGINEERING. THIRD VALVE. BRASS HANDLE. The one that, technically, doesn't "
            "exist. Now MOVE.'"
        )
    world.flags["got_canteen"] = True
    move_item_to_inventory(world, "canteen")
    # The napkin appears on the floor — Tigh drops it during the handoff.
    if "napkin" not in world.inventory and "napkin" not in world.room_items.get("head_deck_5", []):
        move_item_to_room(world, "napkin", "head_deck_5")
    first_wrong = _tigh_next_wrong_name(world)
    second_wrong = _tigh_next_wrong_name(world)
    return (
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
    # If suspicion is already maxed and player keeps talking, fire the ending.
    if _tigh_should_space(world):
        return _tigh_spaced_ending(world)

    if topic is None:
        return _tigh_give_quest(world)

    # Sensitive topics bump his suspicion meter.
    topic_lower = topic.lower()
    if any(danger in topic_lower or topic_lower in danger for danger in TIGH_DANGER_TOPICS):
        _tigh_bump_suspicion(world, 1)

    for key, response in TIGH_TOPICS.items():
        if topic == key or key in topic or topic in key:
            # If asking this nudged him over, the next conversation will trigger spacing.
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
    state = world.npc_state.setdefault("hadrian", {"rumor_index": 0})

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
    state = world.npc_state.setdefault("adama", {"proverb_index": 0})
    p = ADAMA_PROVERBS[state["proverb_index"] % len(ADAMA_PROVERBS)]
    state["proverb_index"] += 1
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
        # He hands it back. The player hasn't figured it out yet.
        return (
            "Admiral Adama takes the napkin between two fingers. He squints at it. "
            "He turns it over. He hands it back to you without comment. 'Specialist. "
            "Some napkins are just napkins.' He turns away. You are dismissed without "
            "having been acknowledged."
        )
    return _adama_hero_ending(world)


def adama_on_talk(world, topic):
    if topic is None:
        return (
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
        return (
            "'Sit down.' She deals. The cards come out crooked because she shuffles\n"
            "like she's beating somebody up. Three rounds in, she discovers you have\n"
            "no money and lose by reflex. She wins all of your shift bonuses for the\n"
            "month. She does not gloat. She just nods, like the universe has finally\n"
            "made sense. 'Get out of my sight, specialist.' She has already forgotten\n"
            "you."
        )

    if topic_lower in ("arm wrestling", "arm", "wrestle", "wrestling"):
        return (
            "She slams her elbow on the table. You slam yours. You make contact. The\n"
            "fight lasts approximately one half of one second. She does not break a\n"
            "sweat. Your arm is now a different shape than it was. 'Better, specialist.\n"
            "I respect that.' She is already looking at someone else. 'NEXT.'"
        )

    if topic_lower in ("making out", "make out", "kiss", "kissing"):
        return (
            "She raises an eyebrow. She raises THE eyebrow. From across the room,\n"
            "Apollo makes a noise that is half whimper and half wedding vow.\n\n"
            "Starbuck stands up. She walks over. She kisses you. It lasts six full\n"
            "seconds. It tastes like cigars, ambrosia, and very specifically a future\n"
            "she has already decided is not yours. She steps back. She wipes her\n"
            "mouth with the back of her hand.\n\n"
            "'You can go now, specialist.' She has already forgotten you.\n\n"
            "Apollo is staring. Apollo's mouth is open. Apollo will need a moment."
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
    if topic is None:
        return (
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
        return (
            "'WHAT.' Long pause. 'WHAT.' He laughs. The laugh is unattached to his\n"
            "face. 'Project Juno is a — that is a — that is classified work,\n"
            "specialist. CLASSIFIED. Move along.'"
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


def _six_increment_entanglement(world, n: int = 1):
    state = world.npc_state.setdefault("six", {"entanglement": 0})
    state["entanglement"] = state.get("entanglement", 0) + n
    return state["entanglement"]


def _six_check_ending(world):
    if world.npc_state.get("six", {}).get("entanglement", 0) >= 3:
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
    ending = _six_check_ending(world)
    if ending is not None:
        return ending

    if topic is None:
        bump = _six_increment_entanglement(world, 1)
        ending = _six_check_ending(world)
        if ending is not None:
            return ending
        hint = SIX_REVEAL_HINTS[(bump - 1) % len(SIX_REVEAL_HINTS)] if bump >= 2 else ""
        text = (
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

    topic_lower = topic.lower()

    if topic_lower in ("self", "name"):
        bump = _six_increment_entanglement(world, 1)
        return (
            "She smiles. The smile is too patient. 'You don't need my name,\n"
            "specialist. You haven't needed my name. You've always known.'"
        )

    if topic_lower in ("cylon", "toaster", "machine", "frakkin' toaster"):
        bump = _six_increment_entanglement(world, 1)
        return (
            "She tilts her head. 'Is that what you think I am?' She does not look\n"
            "offended. She looks delighted. 'That would be... convenient, wouldn't\n"
            "it. To know.'"
        )

    if topic_lower in ("supervisor", "shift", "deck", "twelve"):
        bump = _six_increment_entanglement(world, 1)
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
        bump = _six_increment_entanglement(world, 2)
        return (
            "Her face becomes very still. Very lit. 'God is love, specialist.\n"
            "Love is everything. Everything is becoming. I think you and I are\n"
            "becoming.'"
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
        return (
            "'Pythia is very specific, Specialist. A dying leader. A ragtag fleet.\n"
            "Twelve sources of guidance. And one — I want to be clear — ONE young\n"
            "specialist of dubious provenance who shows up at the right moment with\n"
            "a small folded paper. I have been waiting for the small folded paper.\n"
            "Forgive me for being direct.'"
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
