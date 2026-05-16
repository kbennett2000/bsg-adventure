"""All thirteen-ish rooms of Galactica deck life."""

from random import choice

from engine.models import Room
from engine.registry import register_room
from engine.world import bump_stat, get_stat, move_item_to_room, witness_once


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
        "else to be. There is a service hatch in the deck plate behind the pipes that "
        "you have, professionally, ignored for two years. Taped to the underside of the "
        "fold-down table — you discovered this three weeks ago and have not yet processed "
        "it — is a single playing card. The eight of swords. Nobody has admitted to "
        "putting it there. The card has not moved."
    ),
    exits={"east": "corridor_c12", "out": "corridor_c12"},
    hidden_exits={
        # Service hatch to the algae processor — openable with Tyrol's wrench, or always
        # afterward (the hatch stays unbolted once you've been through it).
        "down": (
            "algae_processor",
            lambda w: "wrench" in w.inventory or w.flags.get("entered_algae_processor", False),
        ),
    },
    items=["algae_bar", "mop", "locker", "console", "bunk"],
    npcs=["hadrian"],
    on_enter=env_control_on_enter,
    on_examine={
        "pipes": "Coolant pipes. They hum. One of them sweats. You have a complicated relationship with that one.",
        "ceiling": "Pipes. Ducts. A handwritten sign that says 'DUCK, DUMBASS.' The sign is below the ducts. It is correct.",
        "rack": "Your rack. Bottom of a three-high stack. Still warm.",
        "hatch": (
            "A service hatch in the deck plate behind the pipes. Bolted shut. The "
            "bolts are deck-grade hex. You would need a heavy-duty wrench to even "
            "pretend to open it. Specifically: Chief Tyrol's wrench. Not by name. "
            "Just by spec. Probably."
        ),
        "service hatch": (
            "A service hatch in the deck plate behind the pipes. Bolted shut. Hex "
            "bolts. Tyrol's frakkin' wrench would do it, if you had it."
        ),
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
    # Stat consequences fire only the FIRST time each encounter type is witnessed.
    # The encounter itself still fires for narrative; the bump is the one-shot.
    seen_key = f"c12_encounter_seen_{key}"
    if not world.flags.get(seen_key):
        world.flags[seen_key] = True
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


def _corridor_c12_roster(world):
    """The duty roster posted on the bulkhead. Examining it shows today's
    chore. Discoverability for the central job tension."""
    from content.duties import render_roster_text
    return render_roster_text(world)


register_room(Room(
    id="corridor_c12",
    name="Corridor C-12",
    short_desc=(
        "Corridor C-12. The deck-five junction. Mess to the north, head to the "
        "east, your bunk to the west. The DUTY ROSTER is posted on the bulkhead."
    ),
    long_desc=(
        "Corridor C-12. A grey hallway with grey lighting illuminating grey people "
        "doing grey jobs. Pipes overhead, deck plates underfoot, melodrama in both "
        "directions. The sign on the bulkhead reads DECK 5 — ENVIRONMENTAL, with an "
        "arrow pointing toward the head and a smaller, hand-scrawled note underneath "
        "that says 'AT YOUR OWN FRAKKIN' RISK.' Beneath the sign, someone has scratched "
        "HELO + SHARON = ?? into the paint. Beneath THAT, in a different hand, the "
        "SHARON has been struck through and replaced with YEARS OF QUESTIONS, which "
        "has, in a third hand, been underlined. Next to it, a fresh xerographed sheet "
        "of paper reads DUTY ROSTER and lists, in regulation block, today's chores."
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
        "roster": _corridor_c12_roster,
        "duty roster": _corridor_c12_roster,
        "duty": _corridor_c12_roster,
        "paper": _corridor_c12_roster,
        "sheet": _corridor_c12_roster,
        "bulletin": _corridor_c12_roster,
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


NIGHT_SHIFT = 4   # See engine.world.SHIFT_NAMES


def head_examine_loose_tile(world):
    """Find Tigh's flask under a loose tile (stash quest bottle #1).
    Findable only at Night — Tigh is passed out and can't catch you."""
    if world.flags.get("found_flask"):
        return (
            "The loose tile is back where it was. The cavity beneath it is empty.\n"
            "You suspect the XO has noticed. You suspect the XO has not noticed.\n"
            "Both possibilities feel correct."
        )
    if "flask" in world.inventory or "flask" in world.room_items.get("head_deck_5", []):
        return "The loose tile is loose. You can see down into the cavity. It is empty now."
    if world.shift != NIGHT_SHIFT:
        # Tigh is awake — he'd notice you fishing under tiles. No reveal.
        return (
            "A perfectly normal floor tile. Slightly loose, maybe. You start to\n"
            "crouch and a low, sober throat-clearing comes from the middle stall.\n"
            "You straighten up. You move on. You will not be doing this with the\n"
            "XO awake."
        )
    world.flags["found_flask"] = True
    bump_stat(world, "suspicion", 5)
    move_item_to_room(world, "flask", "head_deck_5")
    return (
        "One of the tiles near the middle stall is loose. You crouch. You pry it up\n"
        "with the edge of your boot. Underneath, in a cavity that should not exist:\n"
        "a hip flask. Monogrammed S.T.\n\n"
        "From the stall, the snoring continues, even and unbroken. The XO is, by\n"
        "his own loud testimony, asleep."
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
        "unenthusiastic about it. The soap dispenser, on close inspection, contains "
        "hand sanitizer. The hand sanitizer, on closer inspection, contains ambrosia. "
        "Somebody — you note carefully not to ask — has been thinking about this for "
        "a long time."
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
        "tile": head_examine_loose_tile,
        "loose tile": head_examine_loose_tile,
        "tiles": head_examine_loose_tile,
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


MESS_OPEN_SHIFTS = (0, 2)   # Morning Watch, Afternoon (per spec)


def _mess_is_open(world) -> bool:
    return world.shift in MESS_OPEN_SHIFTS


def mess_hall_on_enter(world):
    if not world.flags.get("seen_mess_hall_jump_gossip"):
        world.flags["seen_mess_hall_jump_gossip"] = True
        world.flags["heard_hadrian_jump_gossip"] = True
        base = (
            "Two specialists at the next table are arguing about the next jump. "
            "'Tomorrow.' 'No, today.' 'I heard tonight.' 'It's never when they say.' "
            "They notice you listening, lower their voices, and keep arguing."
        )
    else:
        base = choice(MESS_ENCOUNTERS)
    if not _mess_is_open(world):
        base += (
            "\n\nThe serving line is dark. The kitchen is shuttered. The chairs are "
            "stacked. Mess is closed this watch — comes back open at Morning Watch."
        )
    return base


def _mess_eat(world):
    """The hunger-mechanic entrypoint. Eat a tray; sets ate_today flag."""
    if not _mess_is_open(world):
        return (
            "The serving line is dark, specialist. No food this watch. Try Morning\n"
            "Watch or Afternoon. (Your stomach disagrees with the schedule but the\n"
            "schedule does not care about your stomach.)"
        )
    if world.flags.get("ate_today"):
        return (
            "You already ate today. The lasagna remembers. The lasagna will not have\n"
            "forgotten you between now and tomorrow."
        )
    world.flags["ate_today"] = True
    bump_stat(world, "morale", -1)        # algae lasagna is a vibe
    bump_stat(world, "exhaustion", -3)    # but a vibe with calories
    return (
        "You take a tray. You sit. You eat. The protein is, today, the same protein\n"
        "as yesterday's protein, which is the same protein as the day before's. The\n"
        "cook makes eye contact while you chew. The eye contact is the seasoning."
    )


def mess_hall_examine_kitchen(world):
    """Looking at the kitchen reveals the stash thermos hidden behind serving
    trays. Findable only at Night, when the cook is gone and the kitchen is
    unattended."""
    if world.flags.get("found_stash_mess"):
        return (
            "The kitchen behind the serving line. The thermos slot you saw earlier\n"
            "is empty. You should leave."
        )
    if "stash_bottle_mess" in world.inventory or "stash_bottle_mess" in world.room_items.get("mess_hall", []):
        return "Already disturbed. You should not be in here."
    if world.shift != NIGHT_SHIFT:
        return (
            "The kitchen behind the serving line. The cook is RIGHT THERE. The cook\n"
            "is watching you. The cook is, somehow, also stirring the vat at the\n"
            "same time. You will not be rooting around the kitchen while the cook\n"
            "is in residence."
        )
    world.flags["found_stash_mess"] = True
    bump_stat(world, "suspicion", 5)
    move_item_to_room(world, "stash_bottle_mess", "mess_hall")
    return (
        "The kitchen behind the serving line. The cook is gone — off-shift, off-\n"
        "deck, off-anywhere-you-might-find-them. The kitchen is dark and unmonitored.\n"
        "Partially hidden behind a stack of trays: a thermos labelled COFFEE — DO\n"
        "NOT DRINK — TIGH in three different handwritings."
    )


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
        "You do not have time for this. You take a tray anyway. Above the trash chute, "
        "a small handwritten sign reads 'IF THE CHUTE GROWLS BACK, DO NOT FEED IT.' "
        "Below it, in a different hand: 'AGREED — HADRIAN.' Below THAT, in a third "
        "hand: 'too late.'"
    ),
    exits={
        "south": "corridor_c12",
        "north": "corridor_b",
    },
    items=["tray"],
    npcs=["cook"],
    on_enter=mess_hall_on_enter,
    on_examine={
        "lasagna": "The lasagna. Layers of grey upon grey upon grey. The grey is structural.",
        "protein": (
            "Today's protein is, allegedly, 'reconstituted.' Reconstituted from "
            "what is the question the cook will refuse to answer at increasing "
            "volumes."
        ),
        "meat": (
            "Today's protein is, allegedly, 'reconstituted.' Reconstituted from "
            "what is the question the cook will refuse to answer at increasing "
            "volumes."
        ),
        "mystery meat": (
            "Today's protein is, allegedly, 'reconstituted.' Reconstituted from "
            "what is the question the cook will refuse to answer at increasing "
            "volumes."
        ),
        "tray": "A regulation tray. Three compartments. All grey. The grey is structural.",
        "pilot": "Crying. Tray untouched. Probably named something tragic like Cally or Crash. Definitely doomed.",
        "specialists": "Same specialists you saw last week. Same argument. Same lasagna. Same algae.",
        "table": "Bolted to the deck. The table has been here longer than the war. The table will outlive us all.",
        "kitchen": mess_hall_examine_kitchen,
        "serving line": mess_hall_examine_kitchen,
        "vat": (
            "The protein vat. Large, dented, somehow steaming on both sides. The "
            "vat is older than you are. The vat was not on the original Galactica "
            "manifest. Nobody is sure where it came from. Nobody is asking."
        ),
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
    # One-shot per encounter type — see corridor_c12_on_enter for rationale.
    seen_key = f"b7_encounter_seen_{key}"
    if not world.flags.get(seen_key):
        world.flags[seen_key] = True
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
        "personality. A small stenciled notice next to the fountain reads 'DEEP "
        "CLEAN: 178 DAYS AGO.' The number was 178 when you started this job. The "
        "number was 178 last week. The number, you suspect, is afraid to be any "
        "other number."
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
        "and unresolved feelings. Pinned above the lockers is a hand-drawn relationship "
        "chart of every pilot on the duty roster, with arrows in four different "
        "colors. There are too many arrows. The color code is taped beside the chart "
        "and is, in itself, ALSO an arrow."
    ),
    exits={
        "west": "corridor_b",
        "out": "corridor_b",
    },
    items=["triad_cards"],
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
        "and knows it but is determined not to show it. On the workbench, a coffee "
        "mug bears the legend WORLD'S #1 GAIUS in Baltar's own handwriting. The mug "
        "was, by all available evidence, purchased by Baltar, for Baltar, in a "
        "ceremony attended exclusively by Baltar."
    ),
    exits={
        "east": "corridor_b",
        "out": "corridor_b",
    },
    items=["wrench", "cylon_detector"],
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


def hangar_examine_raptor(world):
    """The hangar stash bottle is hidden in a Raptor's gun port. Night only."""
    if world.flags.get("found_stash_hangar"):
        return (
            "A Raptor. Squat, ugly, beloved. The gun-port slot you stashed nothing in\n"
            "is, conspicuously, empty."
        )
    if "stash_bottle_hangar" in world.inventory or "stash_bottle_hangar" in world.room_items.get("hangar_deck", []):
        return "A Raptor. Squat, ugly, beloved. Recently disturbed by someone. Probably you."
    if world.shift != NIGHT_SHIFT:
        return (
            "A Raptor. Squat, ugly, beloved. Someone has spray-painted 'LUCKY' on\n"
            "the nose. The deck is busy. Deckhands EVERYWHERE. You will not be\n"
            "fishing around in a gun mount during shift. Try off-hours."
        )
    world.flags["found_stash_hangar"] = True
    bump_stat(world, "suspicion", 5)
    move_item_to_room(world, "stash_bottle_hangar", "hangar_deck")
    return (
        "A Raptor. Squat, ugly, beloved. Someone has spray-painted 'LUCKY' on the\n"
        "nose. The paint is fresh. The hangar is quiet at this hour — most of the\n"
        "deckhands are off-shift.\n\n"
        "You walk around the back of it. Tucked into the port-side gun mount — a\n"
        "place where no munition or instrument has any business being — is a\n"
        "regulation grease can. Heavier than a grease can has any business being.\n"
        "It sloshes wrong."
    )


def hangar_examine_floor_panel(world):
    """The cylon-haunted storage bay is only perceivable at high CYLON_VIBES."""
    cv = get_stat(world, "cylon_vibes")
    if cv < 50:
        return (
            "The deck. Plating. Scuffed. The same scuffs you mopped last week. There\n"
            "is nothing unusual about the deck. You feel slightly disappointed."
        )
    return (
        "The deck plate near the back wall is wrong. Not damaged. Not loose. Just\n"
        "wrong. You can see, now — now that you can see — that one of the plates\n"
        "isn't bolted at the corners but HUMS at them. The hum is at four notes.\n"
        "It loops. It loops AGAIN. You take a breath. You should not go down there.\n"
        "You are going to go down there. Down. The exit is down."
    )


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
        "them hit anything. Nobody seems surprised. Spray-painted on a deck plate "
        "near the back wall, in letters the size of a person: IF YOU CAN READ THIS "
        "YOU ARE EITHER A DECKHAND OR HAVE BEEN ON SHIFT TOO LONG. Both apply, "
        "currently, to you."
    ),
    exits={
        "south": "corridor_b",
        "out": "corridor_b",
    },
    hidden_exits={
        # The Cylon-haunted storage bay. You don't see it unless you're already gone enough.
        "down": ("storage_bay", lambda w: get_stat(w, "cylon_vibes") >= 50),
    },
    items=[],
    npcs=["tyrol", "boomer"],
    on_enter=hangar_on_enter,
    on_examine={
        "viper": "A Viper. Beautiful. Lethal. Probably leaking. You are not authorized to fix this one. You wish you were.",
        "raptor": hangar_examine_raptor,
        "raptors": hangar_examine_raptor,
        "wrench": (
            "There's no wrench here. Tyrol's wrench has, by his own account, been "
            "missing for three days. He has not, technically, accused anyone yet."
        ),
        "deck": hangar_examine_floor_panel,
        "floor": hangar_examine_floor_panel,
        "plate": hangar_examine_floor_panel,
        "plates": hangar_examine_floor_panel,
        "back wall": hangar_examine_floor_panel,
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
        "the corner is gently judging your rank. Beside the coffee station, mounted "
        "on the bulkhead, is a small brass plaque: 'OFFICER COUNTRY — SPECIALISTS "
        "WELCOME BY APPOINTMENT.' No appointments have been made, by anyone, ever. "
        "The plaque has, however, been polished."
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
        "same page of a religious text she has been reading for fifteen minutes. "
        "Pinned to the wall above Cottle's desk: a chart titled COTTLE'S RULES. "
        "Seven bullet points. Six of them are blacked out in marker. The seventh, "
        "visible, simply reads: GO AWAY."
    ),
    exits={
        "north": "corridor_a",
        "out": "corridor_a",
    },
    items=["scrolls"],
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


def adama_quarters_examine_drawer(world):
    """Open the desk drawer and find the academy photo."""
    if world.flags.get("found_academy_photo"):
        return (
            "The drawer is open. The photograph is — wherever you put it. You "
            "remember where you put it. You also remember wishing you hadn't put "
            "it anywhere. You remember wishing you hadn't seen it."
        )
    if "photo_academy" in world.inventory or "photo_academy" in world.room_items.get("adamas_quarters", []):
        return "The drawer is half open. There's nothing of consequence left inside."
    world.flags["found_academy_photo"] = True
    move_item_to_room(world, "photo_academy", "adamas_quarters")
    return (
        "You ease the desk drawer open. Inside: pens. A box of cigars. A small\n"
        "bottle of something brown. A pocketwatch, stopped. And, lying face-down\n"
        "at the bottom of the drawer in the specific way that face-down photographs\n"
        "always lie: a photograph.\n\n"
        "You should not turn it over.\n\n"
        "(You're going to turn it over.)"
    )


def adama_quarters_examine_panel(world):
    """The hidden workshop door — only NOTICEABLE if you're suspicious enough."""
    sus = get_stat(world, "suspicion")
    if sus < 40:
        return (
            "Standard officer-grade wall paneling. Wood-trim over insulation. You "
            "look at it. It looks like a wall."
        )
    return (
        "Now that you're looking — now that you're REALLY looking — there's a seam\n"
        "in the paneling. A door-shaped seam. Hinges on the inside. You can see,\n"
        "barely, the outline of a small handle inset flush with the wood. North.\n"
        "Behind the desk. A door that is, technically, not a door. Until you go\n"
        "through it."
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
        "in a way that is, frankly, romantic. You are not supposed to be in here. "
        "On a bookshelf in the corner, wedged between leather-bound regs and the "
        "model-ship manuals, there is a single battered paperback titled POEMS OF "
        "UNREQUITED FRIENDSHIP. The bookmark is on page 47. The bookmark is a "
        "pressed flower."
    ),
    exits={
        "east": "corridor_a",
        "out": "corridor_a",
    },
    hidden_exits={
        # Adama's secret workshop — only visible to a sufficiently paranoid eye.
        "north": ("adamas_workshop", lambda w: get_stat(w, "suspicion") >= 40),
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
        "drawer": adama_quarters_examine_drawer,
        "drawers": adama_quarters_examine_drawer,
        "panel": adama_quarters_examine_panel,
        "wall": adama_quarters_examine_panel,
        "paneling": adama_quarters_examine_panel,
        "seam": adama_quarters_examine_panel,
        "door": adama_quarters_examine_panel,
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
            "down. The drawer below is closed. The drawer is, as drawers go, "
            "intriguing."
        ),
    },
))


# ─── Brig ─────────────────────────────────────────────────────────────────────


def brig_on_enter(world):
    if world.flags.get("entered_brig"):
        return None
    world.flags["entered_brig"] = True
    bump_stat(world, "cylon_vibes", 8)
    return (
        "There is a woman in the cell. She is tall. She is blonde. She is wearing "
        "red. She is sitting calmly. She looks up at you and smiles, slow and "
        "unsettling. She holds eye contact. She does not blink. You wave. She does "
        "not wave back."
    )


def _brig_examine_cell(world):
    """Examining the cell may fulfill the 'escort prisoner' duty for the day."""
    base = "The cell. Reinforced. The reinforcement looks decorative."
    try:
        from content.duties import on_brig_escort
        extra = on_brig_escort(world)
        if extra:
            return base + "\n\n" + extra
    except Exception:
        pass
    return base


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
        "shouldn't be able to see him. Taped to the wall at eye level outside the "
        "cell, in clean block printing: 'DO NOT MAKE EYE CONTACT.' Below it, in a "
        "different hand: 'OR DO. MY CAREER, MY CHOICE. — guard #3'"
    ),
    exits={
        "west": "corridor_a",
        "out": "corridor_a",
    },
    items=[],
    npcs=[],
    on_enter=brig_on_enter,
    on_examine={
        "cell": _brig_examine_cell,
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
        "bench shaped like a single sitting man. You don't sit there. In another "
        "corner, on a small ledge, a glass terrarium contains a single lonely "
        "succulent. The card beside it, in officer-grade calligraphy, reads "
        "'ADAMA SAYS NOT TO ANTHROPOMORPHIZE THE PLANT.' The plant, by your "
        "assessment, has handled the anthropomorphizing itself."
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
        "you yet. Taped to the secondary plot console, in Gaeta's neat handwriting: "
        "'IF DRADIS GOES RED, DO THE THING. IF YOU FORGET WHAT THE THING IS, GAETA "
        "KNOWS THE THING.' Below it, in someone else's hand: 'GAETA IS THE THING.'"
    ),
    exits={
        "south": "corridor_a",
        "out": "corridor_a",
    },
    items=["sealed_envelope"],
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
        "envelope": (
            "A sealed envelope sits on a corner of the secondary plot. Three words "
            "on the front in red marker: DO NOT OPEN. Nobody is guarding it. "
            "Nobody is, in fact, looking at it. The CIC is, despite the activity, "
            "somehow not looking at it."
        ),
    },
))


# ─── Algae Processor (hidden behind environmental control) ────────────────────


def algae_processor_on_enter(world):
    if world.flags.get("entered_algae_processor"):
        return None
    world.flags["entered_algae_processor"] = True
    world.flags["mystery_meat_solved"] = True
    bump_stat(world, "morale", -10)        # what you learn here is upsetting
    bump_stat(world, "cylon_vibes", -3)    # but it's all human, depressingly
    return (
        "The processor.\n\n"
        "There is one vat. The vat is the vat. It is the SAME vat. It has been the\n"
        "same vat since the first attack — you can see this because someone has,\n"
        "in a moment of crew honesty, scratched a tally of every protein cycle into\n"
        "the side. The tally is in the thousands.\n\n"
        "The vat absorbs whatever falls in. You can tell it absorbs whatever falls\n"
        "in because, half-submerged in the surface scum, you can see: a hex bolt.\n"
        "A piece of regulation deck plate. A clearly-once-living rat skeleton. A\n"
        "wristwatch. A set of dog tags belonging to a CREWMAN ENGRAM, last seen\n"
        "three years ago.\n\n"
        "The lasagna is the vat. The vat is the lasagna. You eat the vat. You have\n"
        "always eaten the vat. There has never been a non-vat."
    )


register_room(Room(
    id="algae_processor",
    name="Algae Processor",
    short_desc=(
        "The algae processor. The vat. The truth. Crewman Engram is somewhere in there."
    ),
    long_desc=(
        "A small, hot, humid maintenance bay. One vat, large and slowly turning. "
        "Steam pipes overhead. A single warning sign: PROTEIN CYCLE — DO NOT "
        "BREATHE THROUGH NOSE — ATTEMPT TO BREATHE THROUGH MOUTH AS LITTLE AS "
        "POSSIBLE. The smell is — the smell is its own kind of historical record. "
        "On the workbench in the corner, a small radio is softly playing a song you "
        "don't recognize. Four notes. Then four more. The melody loops. The radio is "
        "unplugged. The radio has not been plugged in since the second war."
    ),
    exits={
        "up": "env_control",
        "out": "env_control",
    },
    on_enter=algae_processor_on_enter,
    on_examine={
        "vat": (
            "The vat. The same vat. The tally on the side reads, by your count,\n"
            "in the thousands. You stop counting. Counting will not help."
        ),
        "tally": (
            "Scratched into the side of the vat: thousands of small vertical marks,\n"
            "in batches of five. Above them, in different handwriting, the word\n"
            "FORGIVE."
        ),
        "rat": "A rat skeleton. Mostly clean. Mostly.",
        "skeleton": "A rat skeleton. Mostly clean. Mostly.",
        "dog tags": (
            "Half-submerged in the surface. The tags belong, by faint stamp, to a\n"
            "CREWMAN ENGRAM. The rest of Engram is not, at this time, fully visible."
        ),
        "tags": (
            "Half-submerged. CREWMAN ENGRAM. He was reported transferred. The transfer\n"
            "paperwork, you suspect, was a lasagna."
        ),
        "sign": (
            "PROTEIN CYCLE — DO NOT BREATHE THROUGH NOSE — ATTEMPT TO BREATHE\n"
            "THROUGH MOUTH AS LITTLE AS POSSIBLE."
        ),
    },
))


# ─── Adama's Secret Workshop ──────────────────────────────────────────────────


def adamas_workshop_on_enter(world):
    if world.flags.get("entered_adamas_workshop"):
        return None
    world.flags["entered_adamas_workshop"] = True
    bump_stat(world, "suspicion", 15)
    return (
        "The door clicks shut behind you. The room is very small. The room is very\n"
        "private. The room is, possibly, the most damning piece of evidence on this\n"
        "ship."
    )


register_room(Room(
    id="adamas_workshop",
    name="Adama's Secret Workshop",
    short_desc=(
        "A small private workshop hidden behind a panel in Adama's quarters. "
        "Two chairs. One workbench. A bottle, a glass. A second glass."
    ),
    long_desc=(
        "A small private workshop, concealed behind the panel in Adama's quarters. "
        "Inside: a workbench. A model ship under construction — DIFFERENT from the "
        "one on the desk, and significantly further along. Two leather chairs, very "
        "close together, facing the bench. Between the chairs, on a low table: a "
        "bottle of ambrosia, half-empty. Two glasses. One has lipstick on it that "
        "is not lipstick. The other is monogrammed, in tiny gold filigree: 'SAUL.'\n\n"
        "There is a photograph on the workbench, propped up, of two young officers "
        "in dress uniform. Hands held below frame.\n\n"
        "On the wall, in a small frame: a single dried flower from Picon. The card "
        "beside it, in Tigh's tight pencil handwriting: 'PICON, 2982. SHE WAS FROM "
        "PICON. HE BOUGHT HER A FLOWER. HE KEPT THE FLOWER. — S.'\n\n"
        "You are looking at a thirty-year affair. You are looking at it from inside.\n"
        "You should leave. You will not leave fast enough."
    ),
    exits={
        "south": "adamas_quarters",
        "out": "adamas_quarters",
    },
    on_enter=adamas_workshop_on_enter,
    on_examine={
        "model": (
            "The model ship. Significantly further along than the one on the desk.\n"
            "Painstaking detail. Tiny brass railings. A pencil note pinned to it:\n"
            "'For Saul's birthday. Don't tell him. — Bill.' The handwriting is\n"
            "Adama's. The date is from before the war."
        ),
        "ship": (
            "The model ship. The REAL one. Painstaking, decades in the making. "
            "The mast is on correctly. The mast was on the OTHER one backwards."
        ),
        "workbench": "Tools laid out with care. Two pairs of reading glasses. Two.",
        "bottle": (
            "Ambrosia. The expensive kind. Half-empty. Two glasses out, both used,\n"
            "one with the unmistakeable rim of someone who has been drinking and\n"
            "crying. Both glasses are warm."
        ),
        "glasses": (
            "Two glasses. One unmonogrammed, lipstick-rimmed (not lipstick). One\n"
            "monogrammed, in gold: 'SAUL.'"
        ),
        "chairs": (
            "Two leather chairs, dragged close together. The arms of the chairs\n"
            "are scuffed in matching places, in the shape of two hands that have\n"
            "been resting on the arms of these chairs, side by side, for a long\n"
            "time."
        ),
        "photo": (
            "The same academy photograph. Different print. This one is framed.\n"
            "This one has been here for decades."
        ),
        "photograph": (
            "The same academy photograph. Different print. This one is framed.\n"
            "This one has been here for decades."
        ),
    },
))


# ─── Cylon-haunted Storage Bay ────────────────────────────────────────────────


def storage_bay_on_enter(world):
    if world.flags.get("entered_storage_bay"):
        return (
            "You're back. The hum is the same. The four notes loop. You feel briefly,\n"
            "embarrassingly, at home."
        )
    world.flags["entered_storage_bay"] = True
    bump_stat(world, "cylon_vibes", 10)
    return (
        "The ladder is short. The space at the bottom is, somehow, much larger than\n"
        "it has any right to be — like the ship grew around something nobody put\n"
        "on the blueprints. The hum is louder down here. The four notes loop.\n\n"
        "You are not alone. There is, in the corner, a figure. The figure is tall.\n"
        "The figure is blonde. The figure is in red. The figure has been waiting.\n"
        "The figure does not move when it sees you. The figure does not need to."
    )


register_room(Room(
    id="storage_bay",
    name="Unused Storage Bay",
    short_desc=(
        "A storage bay that isn't on the manifest. A hum at four notes. Someone "
        "in red, waiting."
    ),
    long_desc=(
        "A storage bay. There are no crates. There are no shelves. There is no\n"
        "manifest. There is, instead: open space. A hum at four notes that loops.\n"
        "Soft light from a source you cannot identify. A figure in red, in the\n"
        "corner. The figure has been here longer than you have been alive. The\n"
        "figure has been here longer than the Galactica has been Galactica.\n\n"
        "Painted on the deck plate in chalk that has not faded: a perfect circle.\n"
        "Inside the circle, in the same hand, one word in block letters: SOON.\n\n"
        "You are calm. You are calm in a way you have not been calm before. This\n"
        "is, on balance, the most alarming part."
    ),
    exits={
        "up": "hangar_deck",
        "out": "hangar_deck",
    },
    on_enter=storage_bay_on_enter,
    on_examine={
        "figure": (
            "She does not look up. She is in red. She is, somehow, the same Six\n"
            "you saw in the corridor. She is, somehow, ALSO a different Six. You\n"
            "stop trying to reconcile this. Reconciling will not help."
        ),
        "hum": "Four notes. The four notes. You know them. You've always known them.",
        "light": "Coming from no fixture. Coming, possibly, from her.",
        "space": (
            "The bay is larger than the deck plates above it suggest. The math is\n"
            "not your concern. The math is, you suspect, being suggested."
        ),
    },
))
