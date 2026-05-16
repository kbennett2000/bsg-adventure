"""All thirteen-ish rooms of Galactica deck life."""

from random import choice

from engine.models import Room
from engine.registry import register_room
from engine.world import bump_stat, move_item_to_room, witness_once


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
    short_desc=(
        "Environmental Control. Your bunk, your locker, your console. Hadrian "
        "is somewhere in the rack stack pretending to be asleep."
    ),
    long_desc=(
        "Environmental Control. Half workshop, half barracks, all yours. Coolant pipes "
        "run across the ceiling at exactly head height for anyone over five-eight, which "
        "is everyone but you and Hadrian, which is one of the reasons you bunk here. A "
        "console in the corner blinks at a rate that feels personal. Your dented locker "
        "stands sentry by your rack. On the small fold-down table beside the bunk, a "
        "half-eaten algae bar waits with the patience of something that has nowhere "
        "else to be."
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


CORRIDOR_C12_ENCOUNTERS = [
    ("tigh_staggers",
     "Colonel Tigh staggers past you muttering something about 'the frakkin' tide.' "
     "He does not see you. He winks at a fire extinguisher and keeps walking."),
    ("starbuck_punches",
     "Lieutenant Thrace rounds the corner. Fists clenched. She makes eye contact "
     "with a bulkhead and PUNCHES it. A rivet pops. She nods at the rivet like it "
     "deserved it and disappears around the next bend."),
    ("six_walks",
     "A tall blonde in a red dress walks past you. Very. Slowly. She turns her "
     "head as she passes and smiles at you. The corridor temperature drops two "
     "degrees and also somehow goes up. You watch her go. So does the bulkhead."),
    ("baltar_argues",
     "Doctor Gaius Baltar is leaning against the bulkhead having a furious "
     "whispered argument with absolutely no one. As you pass, he hisses 'NOT NOW' "
     "at the empty air and shoots you a guilty look. 'I was running calculations. "
     "Out loud. Like a NORMAL person. Why are you LOOKING at me.'"),
    ("apollo_mopes",
     "Captain Apollo brushes past you with the expression of a man trying to "
     "solve algebra during a fistfight. He does not see you. He mutters, 'It's "
     "complicated,' to no one in particular. It is unclear what 'it' is."),
    ("tyrol_yells",
     "Chief Tyrol stomps past with a wrench, shouting at someone over his "
     "shoulder about 'protocol' and 'frakking deck six.' He does not look at "
     "you. He never looks at you. You once worked a sixteen-hour shift together. "
     "He still does not look at you."),
]


def corridor_c12_on_enter(world):
    state = world.npc_state.setdefault("corridor_c12", {"last_encounter": None})
    last = state["last_encounter"]
    candidates = [enc for enc in CORRIDOR_C12_ENCOUNTERS if enc[0] != last]
    key, text = choice(candidates)
    state["last_encounter"] = key
    # Stat consequences for each encounter
    if key == "tigh_staggers":
        bump_stat(world, "suspicion", 4)
    elif key == "starbuck_punches":
        bump_stat(world, "morale", 2)
    elif key == "six_walks":
        world.flags["saw_a_six"] = True
        bump_stat(world, "cylon_vibes", 5)
    elif key == "baltar_argues":
        bump_stat(world, "suspicion", 3)
        bump_stat(world, "morale", -1)
    elif key == "apollo_mopes":
        bump_stat(world, "morale", 1)
    return text


register_room(Room(
    id="corridor_c12",
    name="Corridor C-12",
    short_desc=(
        "Corridor C-12. The deck-five junction. Mess to the north, head to the "
        "east, your bunk to the west."
    ),
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
        "north": "mess_hall",
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
    # First time witnessing the XO drinking in a stall is a load-bearing event.
    witness_once(world, "witnessed_tigh_drinking", "suspicion", 10)
    return (
        "The middle stall door is closed. From inside, you can hear someone humming "
        "the Colonial Anthem off-key. Occasionally there is a long, contemplative "
        "sip."
    )


def head_examine_floor(world):
    """First time the player examines the floor after getting the quest, the napkin
    appears in the room."""
    if not world.flags.get("got_canteen"):
        return (
            "Standard regulation tile. Mopped recently. By you. Last Thursday. There's "
            "a stain near the middle stall that you have made peace with."
        )
    if "napkin" in world.room_items.get("head_deck_5", []) or "napkin" in world.inventory:
        return (
            "The same regulation tile, the same regulation stain, the same crumpled "
            "napkin you already clocked."
        )
    # Spawn the napkin into the room.
    move_item_to_room(world, "napkin", "head_deck_5")
    return (
        "You look down. Tile. Stain. ... and a crumpled napkin near the base of the "
        "middle stall, half-tucked under the partition. The XO must've dropped it "
        "between sips."
    )


def head_examine_stall(world):
    base = (
        "The middle stall door is closed. Through the slats you can see a silhouette "
        "that is unmistakably the XO: shoulders hunched, head tilted, one hand cradling "
        "something rectangular and definitely-not-a-flask."
    )
    if world.flags.get("got_canteen") and "napkin" not in world.room_items.get("head_deck_5", []) and "napkin" not in world.inventory:
        # Free hint toward the floor.
        return base + " There's something on the floor at the base of the door."
    return base


register_room(Room(
    id="head_deck_5",
    name="The Head (Deck 5)",
    short_desc=(
        "The deck-five head. Three stalls, two sinks, one cracked mirror, one "
        "XO of indeterminate sobriety."
    ),
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
        "stall": head_examine_stall,
        "stalls": "Three stalls. One occupied by something approximating a senior officer.",
        "floor": head_examine_floor,
        "tile": head_examine_floor,
        "ground": head_examine_floor,
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


# ─── Mess Hall ────────────────────────────────────────────────────────────────


MESS_ENCOUNTERS = [
    "Two specialists at the next table are debating, very seriously, whether the algae lasagna is real lasagna in the philosophical sense.",
    "A pilot is crying over their tray. Nobody is asking. Everybody is eating slower than usual out of solidarity.",
    "Someone is selling something out of their boot at the corner table. The boot is the menu. The boot is the receipt.",
    "An ensign you don't recognize is on a chair giving an impromptu speech about 'morale.' Nobody is listening. The chair is listening.",
]


def mess_hall_on_enter(world):
    if not world.flags.get("seen_mess_hall_jump_gossip"):
        world.flags["seen_mess_hall_jump_gossip"] = True
        world.flags["heard_hadrian_jump_gossip"] = True  # ambient gossip counts toward jump context
        return (
            "Two specialists at the next table are arguing about the next jump. "
            "'Tomorrow.' 'No, today.' 'I heard tonight.' 'It's never when they say.' "
            "They notice you listening, lower their voices, and keep arguing."
        )
    return choice(MESS_ENCOUNTERS)


register_room(Room(
    id="mess_hall",
    name="Mess Hall",
    short_desc=(
        "The mess. Algae lasagna. Specialists trading gossip. Trays clatter."
    ),
    long_desc=(
        "The mess hall, also known as the algae mines. Long metal tables. Long metal "
        "benches. Long metal silence punctuated by short, urgent gossip. The lunch "
        "special is, as always, lasagna. The lasagna is, as always, algae. A pilot "
        "is sobbing into their tray in the corner. They will be dead by act three. "
        "You do not have time for this. You take a tray anyway."
    ),
    exits={
        "south": "corridor_c12",
        "north": "corridor_b",
    },
    items=[],
    npcs=[],
    on_enter=mess_hall_on_enter,
    on_examine={
        "lasagna": "The lasagna. Layers of grey upon grey upon grey. The grey is structural.",
        "tray": "A regulation tray. Three compartments. All grey. The grey is structural.",
        "pilot": "Crying. Tray untouched. Probably named something tragic like Cally or Crash. Definitely doomed.",
        "specialists": "Same specialists you saw last week. Same argument. Same lasagna. Same algae.",
        "table": "Bolted to the deck. The table has been here longer than the war. The table will outlive us all.",
    },
))


# ─── Corridor B (mid-deck, near hangar) ───────────────────────────────────────


CORRIDOR_B_ENCOUNTERS = [
    ("six_supervisor",
     "Your shift supervisor is leaning against the bulkhead at the corner. Tall. "
     "Blonde. Wearing the deckhand coverall in a way that should be illegal under "
     "Colonial regulation. She sees you and gives you a slow, unreadable smile. You "
     "are not sure if she is your supervisor or a vision."),
    ("six_distant",
     "Down the corridor, a tall blonde in red is walking the OTHER way. She does not "
     "turn around. You very much wanted her to turn around."),
    ("tigh_catwalk",
     "From a catwalk overhead, Colonel Tigh sways gently while saluting a fire "
     "suppression panel with crisp precision. Nobody else seems to see him."),
    ("pilots_yelling",
     "Two pilots stomp past you, mid-shouting-match. 'You said you'd CALL.' 'There "
     "WAS no comms!' 'There's ALWAYS comms!' They round the corner. You hear a "
     "muffled scream. Then making out. Then more screaming."),
    ("ensign_lost",
     "An ensign you've never seen before stops you. 'Specialist — is this Deck Twelve?' "
     "You nod. He nods. He bursts into tears. You walk past."),
]


def corridor_b_on_enter(world):
    state = world.npc_state.setdefault("corridor_b", {"last_encounter": None})
    last = state["last_encounter"]
    candidates = [enc for enc in CORRIDOR_B_ENCOUNTERS if enc[0] != last]
    key, text = choice(candidates)
    state["last_encounter"] = key
    if key == "six_supervisor":
        bump_stat(world, "cylon_vibes", 8)
    elif key == "six_distant":
        bump_stat(world, "cylon_vibes", 3)
    elif key == "tigh_catwalk":
        bump_stat(world, "suspicion", 5)
    elif key == "pilots_yelling":
        bump_stat(world, "morale", 1)
    return text


register_room(Room(
    id="corridor_b",
    name="Corridor B-7",
    short_desc=(
        "Corridor B-7. Mid-deck junction. Hangar one way, mess the other, "
        "drama in every direction."
    ),
    long_desc=(
        "Corridor B-7. A wider corridor than C-12 because this one has to fit pilots "
        "and their egos. The bulkhead has a faded mural that someone in the late "
        "sixties decided was a good idea. There's a Viper-shaped scuff mark at "
        "shoulder height that you choose not to ask about. A drinking fountain "
        "gurgles ominously. The lighting flickers in a way that suggests "
        "personality."
    ),
    exits={
        "south": "mess_hall",
        "east": "pilots_rec",
        "west": "baltars_lab",
        "north": "hangar_deck",
        "up": "corridor_a",
    },
    items=[],
    npcs=["six"],
    on_enter=corridor_b_on_enter,
    on_examine={
        "fountain": "The drinking fountain. The water comes out warm. Nobody is sure why. Nobody asks anymore.",
        "mural": (
            "An abstract mural depicting either the Battle of the Colonies, two "
            "battlestars mating, or a really aggressive bowl of fruit. The artist's "
            "signature has been scratched out. They knew."
        ),
        "scuff": "Viper-shaped. Shoulder height. You move on.",
        "supervisor": "She's looking at you. She's been looking at you. She has been looking at you for some time.",
    },
))


# ─── Pilots' Rec Room ─────────────────────────────────────────────────────────


def pilots_rec_on_enter(world):
    if world.flags.get("entered_pilots_rec"):
        return None
    world.flags["entered_pilots_rec"] = True
    bump_stat(world, "morale", 3)  # the vibes
    return (
        "Two pilots are sobbing and making out in the corner. They will be dead by "
        "act three. You do not have time for this."
    )


register_room(Room(
    id="pilots_rec",
    name="Pilots' Rec Room",
    short_desc=(
        "Pilots' rec. Triad table, smoke haze, two unresolved love triangles, "
        "and an unwiped Viper helmet."
    ),
    long_desc=(
        "The pilots' rec room. Hazy with smoke that the ventilation system is too "
        "polite to address. A triad table in the center, scarred by years of "
        "knife-jabbed punctuation marks. A Viper helmet sits on a shelf, unwashed "
        "for reasons that are nostalgic in the best case. Posters of vipers from "
        "the LAST war. Lockers with names you don't recognize because the names "
        "change every patrol. The whole room smells like aviation fuel, cigar smoke, "
        "and unresolved feelings."
    ),
    exits={
        "west": "corridor_b",
        "out": "corridor_b",
    },
    items=[],
    npcs=["starbuck", "apollo"],
    on_enter=pilots_rec_on_enter,
    on_examine={
        "triad": (
            "The triad table. Two unfinished games. Three loaded sidearms set "
            "casually on the rail. You have learned not to disturb pilot games. "
            "The pilots have learned not to disturb maintenance routines. It is a "
            "good arrangement."
        ),
        "table": (
            "Triad table. Scarred. Sticky in places that no triad rule explains. "
            "There is a betting marker on top: 'IOU one (1) Viper.'"
        ),
        "helmet": (
            "A pilot helmet. Unwashed. Possibly haunted. The name on the inside is "
            "redacted with marker. The marker is starting to fade. You don't want "
            "to know what's under it."
        ),
        "posters": (
            "Posters from the FIRST Cylon war. Pilots smiling. Pilots squinting. "
            "Pilots posing on Vipers. Almost all of them have been crossed out with "
            "a single black line. You stop counting."
        ),
        "lockers": "Pilot lockers. The names rotate. The dents do not.",
        "smoke": "Cigar smoke. Possibly fumarella. Possibly something less regulation. You don't ask.",
    },
))


# ─── Baltar's Lab ─────────────────────────────────────────────────────────────


def baltars_lab_on_enter(world):
    if world.flags.get("entered_baltars_lab"):
        # Re-entry still drains morale (Baltar is exhausting to be near)
        bump_stat(world, "morale", -1)
        return None
    world.flags["entered_baltars_lab"] = True
    witness_once(world, "witnessed_baltar_solo_argument", "suspicion", 5)
    bump_stat(world, "morale", -3)
    bump_stat(world, "cylon_vibes", 2)
    return (
        "Doctor Baltar is in the middle of an argument with no one. He stops "
        "mid-sentence, looks at you, looks back at the empty air, and says — to "
        "the empty air, very pointedly — 'I told you not now.'"
    )


register_room(Room(
    id="baltars_lab",
    name="Baltar's Lab",
    short_desc=(
        "Baltar's lab. Cylon-detection equipment. Baltar. An empty chair he "
        "talks to."
    ),
    long_desc=(
        "Doctor Gaius Baltar's lab. A bewildering quantity of blinking equipment, "
        "wires running into other wires, three terminals running three different "
        "operating systems, and a single elegant chair facing all of it that "
        "appears to be the most important piece of furniture in the room despite "
        "being, as far as you can tell, empty. The lab smells of ozone, expensive "
        "cologne, and the specific flop sweat of a man who is in over his head "
        "and knows it but is determined not to show it."
    ),
    exits={
        "east": "corridor_b",
        "out": "corridor_b",
    },
    items=[],
    npcs=["baltar"],
    on_enter=baltars_lab_on_enter,
    on_examine={
        "chair": (
            "An ergonomic chair. Empty. Definitely empty. There is, however, a "
            "very faint impression in the cushion. The lighting falls on the "
            "impression in a way that is somehow theatrical."
        ),
        "equipment": (
            "Cylon-detection equipment. Or, as far as you can tell from the "
            "blinking lights, a very expensive Christmas display."
        ),
        "terminals": (
            "Three terminals, three operating systems, three sets of running "
            "calculations. You catch one labeled 'PROJECT JUNO.' You catch another "
            "labeled 'PROJECT JUNO (BACKUP).' You catch a third labeled 'NOT "
            "PROJECT JUNO, DEFINITELY.'"
        ),
        "wires": "An academic's wiring job. Functional. Beautiful. Probably about to start a fire.",
    },
))


# ─── Hangar Deck ──────────────────────────────────────────────────────────────


HANGAR_ENCOUNTERS = [
    "A deckhand is sleeping under a Raptor's nose gear. Their snore is rhythmic. The Raptor seems comforted.",
    "A pilot you don't recognize is doing a pre-flight on a ship that is, technically, on fire. The fire is small. The pilot is committed.",
    "Two specialists are arguing about whether a missing wrench was stolen by a Cylon or a different specialist. They are leaning toward Cylon. Out of optimism.",
    "A Raptor's intake belches steam. Three deckhands stare at it. The intake belches steam again. Nobody moves. The Raptor exhales like it's bored of you.",
    "Tyrol shouts something across the deck about 'protocol' and 'frakking deck six' without breaking eye contact with whatever he's holding.",
]


def hangar_on_enter(world):
    return choice(HANGAR_ENCOUNTERS)


register_room(Room(
    id="hangar_deck",
    name="Hangar Deck",
    short_desc=(
        "The hangar. Vipers. Raptors. Grease, sweat, and Chief Tyrol's voice "
        "carrying further than any sane person should allow."
    ),
    long_desc=(
        "The hangar deck. Wide as a small city. Loud as a large one. Vipers in "
        "various states of repair, Raptors in various states of pre-flight, "
        "deckhands in various states of caffeine debt. The air is part oil, part "
        "shouting, part the specific ozone of capital weapons being run through "
        "diagnostic. A LSO is shouting at someone with a clipboard. Someone with "
        "a clipboard is shouting back. Several wrenches are being thrown. None of "
        "them hit anything. Nobody seems surprised."
    ),
    exits={
        "south": "corridor_b",
        "out": "corridor_b",
    },
    items=[],
    npcs=["tyrol", "boomer"],
    on_enter=hangar_on_enter,
    on_examine={
        "viper": "A Viper. Beautiful. Lethal. Probably leaking. You are not authorized to fix this one. You wish you were.",
        "raptor": "A Raptor. Squat, ugly, beloved. Someone has spray-painted 'LUCKY' on the nose. The paint is fresh. Boomer is standing very close to it.",
        "wrench": "A wrench. Inert. Innocent. About to be involved in something.",
    },
))


# ─── Corridor A (upper deck, officer country) ─────────────────────────────────


def corridor_a_on_enter(world):
    if not world.flags.get("seen_officer_country"):
        world.flags["seen_officer_country"] = True
        bump_stat(world, "morale", 2)  # the carpet briefly delights
        return (
            "The lighting up here is better. The carpet is also better. There IS a "
            "carpet up here. You spend a long moment processing this."
        )
    return None


register_room(Room(
    id="corridor_a",
    name="Corridor A (Officer Country)",
    short_desc=(
        "Corridor A. Officer country. Better lighting. Carpet. Bad vibes."
    ),
    long_desc=(
        "Corridor A. The upper deck. This is where officers live, work, and stare "
        "meaningfully out portholes. There is a carpet. Not great carpet, but carpet. "
        "The lighting is warm enough that you suspect mood. There are framed photos "
        "on the bulkhead — battlestars of yesteryear, pilots of yesteryear, the "
        "Quorum of yesteryear. You feel watched by yesteryear. A coffee station in "
        "the corner is gently judging your rank."
    ),
    exits={
        "down": "corridor_b",
        "east": "brig",
        "west": "adamas_quarters",
        "south": "sickbay",
        "up": "observation_deck",
        "north": "cic",
    },
    items=[],
    npcs=[],
    on_enter=corridor_a_on_enter,
    on_examine={
        "carpet": "A real carpet. Officer-issue. There is a stain near the CIC door that looks like coffee but smells like ambrosia. You don't ask.",
        "photos": (
            "Old battlestars. Old pilots. Old wars. One of the photos has a small "
            "card taped to the bottom that says 'COMMANDER ADAMA, FRESH OUT OF "
            "FLIGHT SCHOOL.' He looks twelve. He looks like he is judging you "
            "even at twelve."
        ),
        "coffee": (
            "An officer coffee station. The pot says 'COMMANDER'S COFFEE — DO NOT "
            "TOUCH OR I WILL FRAKKIN' KNOW' in marker. Below: 'agreed - tigh.' "
            "Below THAT: 'do not believe him - tigh.'"
        ),
        "lighting": "Warmer than below. You can't decide if it's lighting or condescension.",
    },
))


# ─── Sickbay ──────────────────────────────────────────────────────────────────


def sickbay_on_enter(world):
    if world.flags.get("entered_sickbay"):
        return None
    world.flags["entered_sickbay"] = True
    return (
        "Doc Cottle is smoking. INSIDE. In SICKBAY. Through his SCRUBS. He sees you "
        "looking. He blows smoke at you. He does not break eye contact."
    )


register_room(Room(
    id="sickbay",
    name="Sickbay",
    short_desc=(
        "Sickbay. Antiseptic smell, cigar smoke. Roslin in a corner chair "
        "reading the same page."
    ),
    long_desc=(
        "Sickbay. Two rows of beds. Most empty. A few not empty in ways you do "
        "not want to examine too closely. Doc Cottle is in the corner, smoking. "
        "His scrubs are blue. His teeth are not. The room smells of antiseptic, "
        "cigar smoke, and the specific copper of a slow afternoon turning into a "
        "fast evening. President Roslin is in a chair near the back, reading the "
        "same page of a religious text she has been reading for fifteen minutes."
    ),
    exits={
        "north": "corridor_a",
        "out": "corridor_a",
    },
    items=[],
    npcs=["roslin", "cottle", "helo"],
    on_enter=sickbay_on_enter,
    on_examine={
        "beds": (
            "Two rows of beds. Most empty. The empty ones are made up. The made-up "
            "ones look like they expect company. You do not like that."
        ),
        "cottle": "Smoking. In sickbay. Through his scrubs. The man has a system.",
        "smoke": "Cigar smoke. The ventilation system has long since stopped trying.",
        "scriptures": "She's reading the same page. She's been reading the same page. The page is not the point.",
        "page": "The same page Roslin has been reading. From here, it looks like Pythia. From any angle, it looks like Pythia.",
    },
))


# ─── Adama's Quarters ─────────────────────────────────────────────────────────


def adamas_quarters_on_enter(world):
    if world.flags.get("entered_adamas_quarters"):
        return None
    world.flags["entered_adamas_quarters"] = True
    # Witnessing the unspoken Bill-and-Saul thing is a load-bearing suspicion event.
    witness_once(world, "witnessed_command_meeting", "suspicion", 15)
    return (
        "Colonel Tigh is already inside. Of course he is. He doesn't look at you. "
        "He looks at the model ship. The model ship does not return the look. The "
        "model ship is small. The silence is large.\n\n"
        "The air in here has a particular density. You should not be in here. You "
        "are going to remember being in here for the rest of your career, however "
        "long or short that turns out to be."
    )


register_room(Room(
    id="adamas_quarters",
    name="Adama's Quarters",
    short_desc=(
        "Adama's quarters. Model ship on the desk. Tigh probably inside, "
        "staring meaningfully at nothing."
    ),
    long_desc=(
        "Admiral Adama's quarters. Wood paneling — actual WOOD, on a battlestar — "
        "and a desk with a model ship on it that he is, allegedly, building. The "
        "model ship has not visibly progressed in three years. Two glasses sit on "
        "the desk. One of them has lipstick on it that is not a woman's. A model "
        "ship sits in dry dock. Two leather chairs face each other across the desk "
        "in a way that is, frankly, romantic. You are not supposed to be in here."
    ),
    exits={
        "east": "corridor_a",
        "out": "corridor_a",
    },
    items=[],
    npcs=[],
    on_enter=adamas_quarters_on_enter,
    on_examine={
        "model": (
            "The model ship. Allegedly being built. Has not progressed in three "
            "years. One mast is on backwards. Nobody has the heart to tell him."
        ),
        "ship": (
            "The model ship. Allegedly being built. Has not progressed in three "
            "years. One mast is on backwards. Nobody has the heart to tell him."
        ),
        "glasses": (
            "Two glasses on the desk. One has lipstick on it. The lipstick is, on "
            "inspection, not lipstick. It is the faintly red rim of someone who "
            "has been drinking ambrosia and crying. You walk away from this glass."
        ),
        "chairs": (
            "Two leather chairs facing each other across the desk. The desk is "
            "small. The chairs are close. The implication is large. You move on."
        ),
        "desk": (
            "A handsome wooden desk. Cluttered with reports, letters, a half-empty "
            "glass of something brown, and one (1) framed photograph turned face "
            "down."
        ),
        "photograph": (
            "Face down. Some impulses you respect. You leave it face down."
        ),
        "photo": (
            "Face down. Some impulses you respect. You leave it face down."
        ),
    },
))


# ─── Brig ─────────────────────────────────────────────────────────────────────


def brig_on_enter(world):
    if world.flags.get("entered_brig"):
        bump_stat(world, "cylon_vibes", 2)
        return None
    world.flags["entered_brig"] = True
    bump_stat(world, "cylon_vibes", 8)
    return (
        "There is a woman in the cell. She is tall. She is blonde. She is wearing "
        "red. She is sitting calmly. She looks up at you and smiles, slow and "
        "unsettling. She holds eye contact. She does not blink. You wave. She does "
        "not wave back."
    )


register_room(Room(
    id="brig",
    name="The Brig",
    short_desc=(
        "The brig. One cell. One occupant. Tall. Blonde. Red. Calm."
    ),
    long_desc=(
        "The brig. One cell — Galactica has had to expand this. The cell has "
        "reinforced viewing panels. The reinforced viewing panels have visible "
        "fingerprints on them from the inside. The cell's occupant is a tall "
        "blonde woman in a red dress. She is sitting in a meditation posture. She "
        "appears to be expecting you. A guard at the door has the thousand-yard "
        "stare of a man who has been making eye contact too long with somebody who "
        "shouldn't be able to see him."
    ),
    exits={
        "west": "corridor_a",
        "out": "corridor_a",
    },
    items=[],
    npcs=[],
    on_enter=brig_on_enter,
    on_examine={
        "cell": "The cell. Reinforced. The reinforcement looks decorative.",
        "woman": "Tall. Blonde. Red. Smiling. You can't tell if you're being assessed for a date or for parts.",
        "blonde": "Smiling. Holding eye contact. You blink first. She wins.",
        "guard": "The guard. He has the eyes of a man who has stopped praying.",
        "fingerprints": (
            "Fingerprints on the inside of the viewing panel. From the inside. "
            "Pressed firmly. They are arranged in a pattern. The pattern looks "
            "almost like a smiley face. Almost."
        ),
    },
))


# ─── Observation Deck ─────────────────────────────────────────────────────────


def observation_on_enter(world):
    if not world.flags.get("entered_observation"):
        world.flags["entered_observation"] = True
        return (
            "Captain Apollo is here. Of course he is. He is staring out the porthole "
            "with the expression of a man trying to do long division about a person."
        )
    return None


register_room(Room(
    id="observation_deck",
    name="Observation Deck",
    short_desc=(
        "Observation deck. Stars. A porthole. Apollo, brooding professionally."
    ),
    long_desc=(
        "The observation deck. A long viewing window onto the void. Stars. Other "
        "ships of the fleet, drifting in formation. The colonial flag hangs in one "
        "corner because, you suppose, somebody has to hang it somewhere. A bench "
        "runs the length of the window. The bench has been polished by decades of "
        "officers brooding very hard onto it. There is a faint impression in the "
        "bench shaped like a single sitting man. You don't sit there."
    ),
    exits={
        "down": "corridor_a",
        "out": "corridor_a",
    },
    items=[],
    npcs=["apollo"],
    on_enter=observation_on_enter,
    on_examine={
        "stars": "Stars. Always more stars. The math of stars is unfriendly to humans, but the LOOK of stars is forgiving.",
        "porthole": "Thick. Reinforced. Cleaned recently. By you. Last Wednesday.",
        "window": "Thick. Reinforced. Cleaned recently. By you. Last Wednesday.",
        "bench": (
            "A bench polished by brooding. There is an impression on it that is "
            "very specifically Apollo-shaped. You can see two more vague "
            "impressions on either side, like ghosts of broods past."
        ),
        "fleet": "Civilian ships in loose formation. Their lights blink at irregular intervals. From here, the fleet looks like a slow constellation. From up close, it is mostly arguments.",
        "flag": "The Colonial flag. Hung crooked. Nobody has fixed it. Nobody will fix it. The crookedness is the point now.",
    },
))


# ─── CIC ──────────────────────────────────────────────────────────────────────


def cic_on_enter(world):
    world.flags["heard_intercom_jump_prep"] = True
    if not world.flags.get("entered_cic"):
        world.flags["entered_cic"] = True
        bump_stat(world, "morale", 4)       # you snuck into CIC, that rules
        bump_stat(world, "suspicion", 3)    # but you ARE on camera
        return (
            "An ensign at a console is saying 'JUMP PREP IN PROGRESS' into a "
            "headset for the third time. Another ensign is replotting coordinates "
            "from a clipboard. The clipboard is shaking. The ensign is also "
            "shaking. The Admiral is at the central plot, hands clasped behind his "
            "back, doing the thing he does where he looks at nothing meaningfully."
        )
    return (
        "The jump-prep ensign is still saying 'JUMP PREP IN PROGRESS' into the "
        "headset. They have not blinked since you arrived."
    )


register_room(Room(
    id="cic",
    name="Combat Information Center (CIC)",
    short_desc=(
        "CIC. Lit dark, full of consoles, hummed prayers, ensigns vibrating "
        "with stress. Adama at the plot."
    ),
    long_desc=(
        "Combat Information Center. The bridge, the heart, the room where Bad "
        "Things are handled by Good Officers with set jaws and unsteady hands. "
        "Consoles glow in the dim. The DRADIS scope sweeps. Junior officers murmur "
        "into headsets. Senior officers stand around the central plot with the "
        "specific stillness of people who have decided that gravitas IS the job. "
        "Admiral Adama is at the plot. The plot is illuminated. The plot is "
        "displaying a jump vector that is, conspicuously, NOT YET ENTERED. "
        "Specialists are not supposed to be in here. Nobody seems to have noticed "
        "you yet."
    ),
    exits={
        "south": "corridor_a",
        "out": "corridor_a",
    },
    items=[],
    npcs=["adama", "gaeta", "dualla"],
    on_enter=cic_on_enter,
    on_examine={
        "plot": (
            "The central plot table. A jump vector is displayed, but the "
            "destination coordinates field is BLANK. The XO is supposed to have "
            "filed them. The XO is, last you checked, in a toilet stall."
        ),
        "consoles": "Banks of consoles. Ensigns at every station. Every screen is amber and urgent.",
        "dradis": "The DRADIS scope. Sweeping. Nothing on it. Yet. The 'yet' is the point.",
        "ensigns": (
            "Junior officers, all of them with the specific look of people who are "
            "not being paid enough and know it. One of them mouths 'help me' at "
            "you. You're not sure if it's meant for you. You move on."
        ),
        "adama": "The Old Man. At the plot. Hands clasped. Staring at something that isn't there. You feel like you shouldn't be here. You also feel like nobody is going to stop you.",
        "scope": "The DRADIS scope. Sweeping. Nothing on it. Yet.",
    },
))
