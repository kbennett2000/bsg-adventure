"""Three rooms for the opening slice."""

from random import choice

from engine.models import Room
from engine.registry import register_room


# ─── Environmental Control (player's bunk) ────────────────────────────────────


def env_control_on_enter(world):
    if world.flags.get("seen_intercom_page"):
        return None
    world.flags["seen_intercom_page"] = True
    name_upper = world.player_name.upper()
    return (
        "The intercom crackles to life with the urgency of a wet engine starting.\n\n"
        f"  INTERCOM: ATTENTION SPECIALIST {name_upper}. REPORT TO THE DECK FIVE\n"
        f"  HEAD IMMEDIATELY. INTERCOM: REPEAT. SPECIALIST {name_upper}. DECK FIVE\n"
        "  HEAD. AT THE FRAKKIN' DOUBLE. INTERCOM: OUT.\n\n"
        "Crewman Hadrian, lying in the next bunk over with a deck of cards balanced "
        "on his chest, peers at you over the top of the eight of swords.\n\n"
        "'Oh,' he says. 'That's YOU, isn't it.'\n\n"
        "He grins. 'XO sounds extra wet today. Good luck, specialist. Wear a mask.'"
    )


register_room(Room(
    id="env_control",
    name="Environmental Control",
    short_desc="Your bunk in environmental control.",
    long_desc=(
        "Environmental Control. Half workshop, half barracks, all yours. Coolant pipes "
        "run across the ceiling at exactly head height for anyone over five-eight, which "
        "is everyone but you and Hadrian, which is one of the reasons you bunk here. A "
        "console in the corner blinks at a rate that feels personal. Your dented locker "
        "stands sentry by your rack. On the small fold-down table beside the bunk, a "
        "half-eaten algae bar waits with the patience of something that has nowhere else "
        "to be."
    ),
    exits={"east": "corridor_c12", "out": "corridor_c12"},
    items=["algae_bar", "mop", "locker", "console", "bunk"],
    npcs=["hadrian"],
    on_enter=env_control_on_enter,
    on_examine={
        "pipes": "Coolant pipes. They hum. One of them sweats. You have a complicated relationship with that one.",
        "ceiling": "Pipes. Ducts. A handwritten sign that says 'DUCK, DUMBASS.' The sign is below the ducts. It is correct.",
        "rack": "Your rack. Bottom of a three-high stack. Still warm.",
    },
))


# ─── Corridor C-12 ────────────────────────────────────────────────────────────


CORRIDOR_ENCOUNTERS = [
    (
        "tigh_staggers",
        "Colonel Tigh staggers past you muttering something about 'the frakkin' tide.' "
        "He does not see you. He winks at a fire extinguisher and keeps walking."
    ),
    (
        "starbuck_punches",
        "Lieutenant Thrace rounds the corner. Fists clenched. She makes eye contact "
        "with a bulkhead and PUNCHES it. A rivet pops. She nods at the rivet like it "
        "deserved it and disappears around the next bend."
    ),
    (
        "six_walks",
        "A tall blonde in a red dress walks past you. Very. Slowly. She turns her "
        "head as she passes and smiles at you. The corridor temperature drops two "
        "degrees and also somehow goes up. You watch her go. So does the bulkhead."
    ),
    (
        "baltar_argues",
        "Doctor Gaius Baltar is leaning against the bulkhead having a furious "
        "whispered argument with absolutely no one. As you pass, he hisses 'NOT NOW' "
        "at the empty air and shoots you a guilty look. 'I was running calculations. "
        "Out loud. Like a NORMAL person. Why are you LOOKING at me.'"
    ),
    (
        "apollo_mopes",
        "Captain Apollo brushes past you with the expression of a man trying to "
        "solve algebra during a fistfight. He does not see you. He mutters, 'It's "
        "complicated,' to no one in particular. It is unclear what 'it' is."
    ),
    (
        "tyrol_yells",
        "Chief Tyrol stomps past with a wrench, shouting at someone over his "
        "shoulder about 'protocol' and 'frakking deck six.' He does not look at "
        "you. He never looks at you. You once worked a sixteen-hour shift together. "
        "He still does not look at you."
    ),
]


def corridor_c12_on_enter(world):
    state = world.npc_state.setdefault("corridor_c12", {"last_encounter": None})
    last = state["last_encounter"]
    candidates = [enc for enc in CORRIDOR_ENCOUNTERS if enc[0] != last]
    key, text = choice(candidates)
    state["last_encounter"] = key
    if key == "six_walks":
        world.flags["saw_a_six"] = True
    return text


register_room(Room(
    id="corridor_c12",
    name="Corridor C-12",
    short_desc="A junction corridor on deck five.",
    long_desc=(
        "Corridor C-12. A grey hallway with grey lighting illuminating grey people "
        "doing grey jobs. Pipes overhead, deck plates underfoot, melodrama in both "
        "directions. The sign on the bulkhead reads DECK 5 — ENVIRONMENTAL, with an "
        "arrow pointing toward the head and a smaller, hand-scrawled note underneath "
        "that says 'AT YOUR OWN FRAKKIN' RISK.'"
    ),
    exits={
        "west": "env_control",
        "east": "head_deck_5",
    },
    items=[],
    npcs=[],
    on_enter=corridor_c12_on_enter,
    on_examine={
        "sign": "It says: DECK 5 — ENVIRONMENTAL. Beneath, in pen: 'AT YOUR OWN FRAKKIN' RISK.' Beneath THAT, in a different pen: 'agreed - hadrian.'",
        "pipes": "Pipes. The maintenance log was your problem last week. The leak is somebody else's problem this week. The pipes do not care.",
        "deck": "Standard deck plating. Scuffed. Recently mopped. By you, probably. Last Tuesday.",
        "six": "She's gone. The corridor smells faintly of cinnamon and impending career consequences.",
        "starbuck": "Already gone. There's a fresh dent in the bulkhead the shape of her knuckles.",
        "tigh": "Already gone. The fire extinguisher he winked at looks vaguely flattered.",
        "baltar": "Already gone. He took the empty air with him.",
        "apollo": "Already gone. The faint smell of cologne and bad decisions lingers.",
    },
))


# ─── The Head (Deck 5) ────────────────────────────────────────────────────────


def head_on_enter(world):
    if world.flags.get("entered_head"):
        return None
    world.flags["entered_head"] = True
    return (
        "The middle stall door is closed. From inside, you can hear someone humming "
        "the Colonial Anthem off-key. Occasionally there is a long, contemplative "
        "sip."
    )


register_room(Room(
    id="head_deck_5",
    name="The Head (Deck 5)",
    short_desc="Deck five latrine. Smells like duty.",
    long_desc=(
        "The Deck 5 head. Three stalls, two sinks, one cracked mirror. The fluorescent "
        "light above the mirror buzzes like a dying wasp. There is a sign above the "
        "sinks that says 'WASH YOUR FRAKKIN' HANDS' in three languages, two of them "
        "rude. The middle stall door is closed. The other two are open and "
        "unenthusiastic about it."
    ),
    exits={
        "west": "corridor_c12",
        "out": "corridor_c12",
    },
    items=[],
    npcs=["tigh"],
    on_enter=head_on_enter,
    on_examine={
        "stall": (
            "The middle stall door is closed. Through the slats you can see a silhouette "
            "that is unmistakably the XO: shoulders hunched, head tilted, one hand cradling "
            "something rectangular and definitely-not-a-flask."
        ),
        "stalls": "Three stalls. One occupied by something approximating a senior officer.",
        "mirror": (
            "Cracked. Your reflection looks tired. You make eye contact with yourself. "
            "Your reflection blinks first."
        ),
        "sink": "Standard sink. The hot water tap is labeled 'COLD' in marker. It is correct.",
        "sinks": "Two sinks. Both with the hot/cold labels switched. The marker is on the floor.",
        "sign": "WASH YOUR FRAKKIN' HANDS. In three languages. Two of them rude.",
        "light": "Fluorescent. Buzzing. Either dying or composing a symphony. Possibly both.",
    },
))
