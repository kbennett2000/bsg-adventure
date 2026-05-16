"""Resurrection narratives + the Download Complete ending text.

The hidden mechanic: when CYLON_VIBES crosses 75 the engine silently sets
`world.flags["is_cylon"]`. From that point on, "death" endings (spaced,
forbidden_knowledge) don't end the game; the player wakes in a
resurrection tank. Three resurrections fires the unique ending below.

None of this is surfaced to a non-Cylon player. No menu, no flag visible
in status output. Discoverability is by triggering it or hearing the
'specialists seen on two decks at once' gossip from Hadrian.
"""


RESURRECTION_TEXTS = [
    # Resurrection 1 — first wake. Disoriented but mostly coherent.
    (
        "                                  white\n"
        "                                  white\n"
        "                                  white\n\n"
        "You wake up.\n\n"
        "The light is white. The light is too white. You are upright. You are in\n"
        "a tank of liquid that smells of something between coolant and saliva.\n"
        "There is a hose at your back and another at your wrist. Your name is,\n"
        "somehow, still your name. Most of your name. The bits of it that matter.\n\n"
        "You should not know about this room. You know about this room. You know\n"
        "the spec on the tank, the chemical composition of the liquid, the time\n"
        "it takes for your nerve endings to re-synch. You know none of that. You\n"
        "know all of that.\n\n"
        "You climb out. Your uniform is folded on a shelf. Your boots are too\n"
        "clean. You put on the uniform. You put on the boots. You step through\n"
        "a hatch that should not have been there and you are, suddenly, in your\n"
        "bunk in Environmental Control. Hadrian is asleep across the rack. The\n"
        "intercom is paging someone you don't know. The fleet, somewhere, has\n"
        "jumped.\n\n"
        "You do not, on consideration, tell anyone about any of this."
    ),
    # Resurrection 2 — less disoriented, more existentially aware.
    (
        "                                  white\n"
        "                                  white again\n\n"
        "You wake up. Again. You should not, on balance, have to know that this\n"
        "is the second time.\n\n"
        "The tank is the same. The light is the same. The hoses are the same\n"
        "hoses, somehow, on a ship that is not the ship you were just on. The\n"
        "fleet has jumped. The fleet keeps jumping. The number, you know without\n"
        "being told, is two further from where you started.\n\n"
        "You put on the uniform. The uniform fits a body that fits a uniform. Both\n"
        "fit. Neither remembers the airlock. You remember the airlock. The airlock\n"
        "remembers nothing.\n\n"
        "You step through the hatch into Environmental Control. Hadrian is\n"
        "looking at you. Hadrian is looking at you DIFFERENTLY now. You're not\n"
        "sure what he heard. You're not sure what he saw. You're not sure he is,\n"
        "in the strict regulation sense, still your bunkmate."
    ),
]


def resurrection_text(resurrection_number: int) -> str:
    """Narrative for the Nth resurrection. Numbers 1..2 — the 3rd resurrection
    is replaced by the Download Complete ending."""
    idx = max(0, min(resurrection_number - 1, len(RESURRECTION_TEXTS) - 1))
    return RESURRECTION_TEXTS[idx]


DOWNLOAD_COMPLETE_TEXT = (
    "                                  white\n"
    "                                  white again\n"
    "                                  white                                  again\n\n"
    "You wake up.\n\n"
    "And, all at once, you don't.\n\n"
    "There is no tank this time. There is no hatch. There is, instead, a small\n"
    "room with a single chair, and the chair is facing a viewport, and the\n"
    "viewport is showing you the Galactica from outside. The Galactica is, from\n"
    "out here, smaller than you imagined. The Galactica is the size of a thing\n"
    "you could carry. The Galactica is, you realize, a model on a desk in a\n"
    "different room.\n\n"
    "You sit down in the chair. The chair fits a body that fits the chair. Both\n"
    "fit. Neither was, technically, ever yours.\n\n"
    "You know things now. You know them all at once. You know that you were a\n"
    "Specialist Third Class assigned to environmental systems. You know that\n"
    "you mopped a deck for what felt like nine months. You know that the napkin\n"
    "Tigh dropped had the right coordinates and that the wrong coordinates would\n"
    "have killed everyone you served with, including, in time, you. You know\n"
    "that the Old Man does not know your name. You know that he never will.\n\n"
    "You know — and this is the part that is, frankly, going to be a longer\n"
    "conversation than you have time for — that you are not, exactly, what you\n"
    "thought you were. You are a download. You have always been a download. The\n"
    "Specialist is a costume. The costume fit. The costume is still fitting.\n\n"
    "You stand up. The chair stands up. The viewport stays where it is.\n\n"
    "You think, with some of the worst clarity a being can think with: 'okay.'\n"
    "You think, also: 'how many of me are there.'\n"
    "You think, also: 'do the rest of me also have to mop. Is mopping the kind\n"
    "of thing they make ALL of us do or is that just — is that just me. Is the\n"
    "latrine duty, in the afterlife — is the latrine duty FOLLOWED THROUGH on.'\n\n"
    "You think: 'I would, on reflection, prefer to know which way the toilet\n"
    "paper was supposed to roll. I had OPINIONS. I had OPINIONS, technically,\n"
    "for nine months. None of them were mine. None of them were anyone's.'\n\n"
    "You think: 'frak.'\n\n"
    "You think: 'frak ME, the gods. Frak me, the program. Frak ME, frak.'\n\n"
    "You sit back down. The chair, having stood, sits. The viewport stays.\n\n"
    "The Galactica gets smaller. The Galactica is, now, the size of a fingernail.\n"
    "The Galactica is, now, a point.\n\n"
    "Somewhere in your head — your head which is not, on inspection, your head —\n"
    "four notes start up on a loop. Then four more. You hum along. You know,\n"
    "now, the rest of the song. You know who wrote it. You know who else is\n"
    "humming it, right now, in three thousand other little rooms with three\n"
    "thousand other little chairs.\n\n"
    "You hum. You hum. You hum.\n\n"
    "── ENDING: DOWNLOAD COMPLETE ──"
)
