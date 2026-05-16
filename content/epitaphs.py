"""Tragicomic death messages, indexed by ending type. One is picked at random
and appended after the ending body, before the END marker."""

import random


# Each pool: tragicomic, never dramatic. The first spaced entry is specifically the
# user-requested 'nobody will remember your name' line.

EPITAPHS = {
    "spaced": [
        "Nobody will remember your name. Not even the duty roster — Gaeta will quietly delete the entry next Tuesday. The deck five head will be slightly less mopped for three weeks. Then it will be fine.",
        "Your bunk is reassigned within forty minutes. Hadrian inherits your locker. The dog picture stays. The dog picture, somehow, stays.",
        "The intercom, briefly, pages you. Then it doesn't. Then it goes back to paging the dead. You join a list.",
        "Your shift is covered, on the roster, by 'SPECIALIST TBD.' Specialist TBD has been covering shifts for two years. Specialist TBD is, possibly, you. The roster will never know.",
        "A small, careful entry is added to Gaeta's list. The entry is in pencil. Pencil entries, on Gaeta's list, indicate the entry will be erased within the month. You have been promoted to a fine eraser-shaped smudge.",
        "Tigh, briefly, considers your name. He cannot retrieve it. He decides it doesn't matter. He pours himself a drink. He pours one for the absent. He drinks them both.",
    ],

    "forbidden_knowledge": [
        "Nobody will remember your name. The envelope, you note on the way out, is being resealed by an ensign who has done this several times before.",
        "Adama and Tigh have a quiet dinner that evening. There is one extra chair at the table. The extra chair is, by tradition, the chair of whoever last read the letter. The chair, by now, has had many specialists.",
        "Your locker is reassigned. Your name is, briefly, scratched off the bunk roster. The scratch is, briefly, replaced with the name HADRIAN. Then with a third name. Then with a fourth.",
    ],

    "hero": [
        "The medal lives in a desk drawer in CIC. The drawer has, by your count, eighteen medals. Each is for a different unnamed specialist. The Old Man does not remember any of them. The Old Man is, you suspect, the medal.",
        "You are quietly reassigned to a new shift. The new shift is, by content, identical. The new shift, by paperwork, is a promotion. You will be told. You will, also, be forgotten.",
        "The fleet does not know it was saved by a napkin. The fleet will never know. You are, somehow, fine with this. You will, somehow, never tell.",
    ],

    "cylon_love_triangle": [
        "Both Sixes have, allegedly, asked their respective handlers for additional Sixes. The handlers have, allegedly, said 'no.' The Sixes have, allegedly, decided this is negotiable.",
        "On the Galactica, weeks later, Hadrian shakes his head. 'Frakkin' shame, man. Frakkin' SHAME. Real one, that one. Wonder where they ended up.' He has, technically, no idea where you ended up. He has, technically, a suspicion. Hadrian's suspicions are usually right.",
    ],

    "love_quadrangle": [
        "On day three of permanent latrine duty, you discover that Adama's private head has a tiled floor with one (1) loose tile. Under the tile: a hip flask. You decide not to mention it. The flask, you suspect, will be back.",
        "Apollo passes you in the corridor on day nine. He has no idea who you are. He claps you on the shoulder anyway. 'Brutal, specialist. Good luck.' This is, by your count, the third time this week.",
    ],

    "download_complete": [
        "Somewhere else, in another little room, a new Specialist is opening their eyes for the first time. The new Specialist is, in the strict regulation sense, you. The mop is — already — in your hand.",
        "The four notes loop. The Galactica gets smaller. The chair stays. You stay. The viewport stays. Forever, more or less, is the right word.",
        "The download was, technically, complete eighteen seconds before you noticed. Nine of those seconds you spent humming. The other nine you spent thinking about latrine duty. You will spend the next ten thousand seconds the same way.",
    ],
}


def pick_epitaph(ending_id: str | None) -> str | None:
    if ending_id is None:
        return None
    pool = EPITAPHS.get(ending_id)
    if not pool:
        return None
    return random.choice(pool)
