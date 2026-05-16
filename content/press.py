"""The Quorum Press Conference minigame.

Triggered by Roslin's `talk to roslin about press` topic (the player gets
shoved in front of the press because everyone more important is indisposed —
Tigh drunk, Adama with Tigh, Baltar talking to no one).

Mechanics:
  - 6 rounds of reporter questions, each with 3 response categories:
        * honest   — true, raises suspicion, sometimes funny
        * political — safe, lowers morale (it is soul-death)
        * unhinged — chaos, large random stat swings, occasionally accidental win
  - Credibility tracked across rounds (start 50, range 0..100)
  - Roslin stage-whispers between rounds
  - Outcomes:
        ≥ 70  : high — Roslin impressed, awards a commendation letter
        ≤ 10  : rock bottom — briefly famous; "was_briefly_famous" flag for later
        ≤ 30  : low — accidentally confirm conspiracies, suspicion +30 fleet-wide
        else  : medium — no special outcome, just the per-round stat impact

State lives in world.flags so the conference round-trips through save/load
naturally. The engine session loop intercepts input when `press_active` is set
and routes it through `handle_input` below."""

import random

from engine.commands import HandlerResult
from engine.world import bump_stat, get_stat, move_item_to_inventory


# ─── question pool ────────────────────────────────────────────────────────────

QUESTIONS = [
    {
        "id": "election",
        # Parody: Roslin vs Baltar election arc
        "question": (
            "REPORTER (Quorum News): 'Specialist, the President's polling numbers\n"
            "have collapsed since the latest jump. The Quorum is openly pushing\n"
            "Doctor Baltar as a candidate in the next election. Where do you stand?'"
        ),
        "honest": {
            "text": (
                "You say: 'Doctor Baltar talks to himself. Constantly. Loudly. I\n"
                "have personally witnessed him having an argument WITH AND ABOUT\n"
                "an empty chair for forty-five minutes. He should not, in my\n"
                "specialist opinion, be the President of anything.'\n\n"
                "ROSLIN (stage whisper): 'Frak, specialist — that was actually fine.'"
            ),
            "delta": {"credibility": 8, "suspicion": 4, "morale": 2},
        },
        "political": {
            "text": (
                "You say: 'The President of the Twelve Colonies has, at this time,\n"
                "the full confidence of the fleet. I am not, at this time, in a\n"
                "position to comment further on internal Quorum dynamics.'\n\n"
                "ROSLIN (stage whisper): '...adequate.'"
            ),
            "delta": {"credibility": 5, "morale": -3},
        },
        "unhinged_text": (
            "You say: 'I think the Cylons should run. They've got better paperwork,\n"
            "frankly, and at least one of them is RIGHT THERE.' You point at, by\n"
            "complete accident, the venerable Quorum chair from Sagittaron.\n"
        ),
        "unhinged_outcomes": [
            {
                "credibility": 18, "morale": 8,
                "note": ("The Sagittaron delegate laughs. The Sagittaron delegate "
                         "laughs AGAIN. The Sagittaron delegate laughs for the next "
                         "twenty seconds and somehow the press room laughs with him.\n"
                         "ROSLIN (stage whisper): 'HOW.'"),
            },
            {
                "credibility": -20, "suspicion": 8,
                "note": ("The Sagittaron delegate stops laughing. The Sagittaron\n"
                         "delegate has, you note, friends.\n"
                         "ROSLIN (stage whisper): 'I'm going to space you myself.'"),
            },
            {
                "credibility": -5, "cylon_vibes": 6,
                "note": ("Three reporters write down the word 'CYLONS' and underline\n"
                         "it. Twice. ROSLIN (stage whisper): 'No.'"),
            },
        ],
    },
    {
        "id": "abortion",
        # Parody: Roslin's executive order on reproduction in 'The Captain's Hand'
        "question": (
            "REPORTER (Caprica Daily): 'Madam President recently signed an\n"
            "executive order regarding civilian reproductive policy aboard the\n"
            "fleet. Many call it controversial. Your reaction?'"
        ),
        "honest": {
            "text": (
                "You say: 'I'm a specialist. I clean toilets. I reroute coolant. I\n"
                "have not, technically, been briefed on civilian reproductive\n"
                "policy. I have OPINIONS, none of them informed.'\n\n"
                "ROSLIN (stage whisper): 'Stop talking. Stop talking. Stop—'"
            ),
            "delta": {"credibility": 2, "suspicion": 3, "morale": 1},
        },
        "political": {
            "text": (
                "You say: 'The order represents one of many difficult decisions\n"
                "the President has been called upon to make in trying times. I\n"
                "trust her judgment.'\n\n"
                "ROSLIN (stage whisper): 'Better.'"
            ),
            "delta": {"credibility": 6, "morale": -4},
        },
        "unhinged_text": (
            "You say: 'There aren't enough HEADS on this ship to make new heads\n"
            "worth the math. Where would we PUT them. Have you SEEN the bunk\n"
            "rotation. Have you SEEN the algae?'\n"
        ),
        "unhinged_outcomes": [
            {
                "credibility": 12, "morale": 5,
                "note": ("Three reporters nod, slowly, with the specific nod of\n"
                         "people who have been on bunk rotation themselves.\n"
                         "ROSLIN (stage whisper): 'You're not WRONG.'"),
            },
            {
                "credibility": -15, "suspicion": 7,
                "note": ("The Quorum delegate from Picon stands up. The Quorum\n"
                         "delegate from Picon sits down. The Quorum delegate from\n"
                         "Picon stands up again. ROSLIN (stage whisper): 'I will\n"
                         "remember this.'"),
            },
        ],
    },
    {
        "id": "cylons_among_us",
        # Parody: the central paranoia of the entire show
        "question": (
            "REPORTER (Colonial Press): 'Specialist, persistent reports indicate\n"
            "Cylon agents may have infiltrated the fleet. Are there Cylons among\n"
            "us?'"
        ),
        "honest": {
            "text": (
                "You say: 'I mean — listen — my shift supervisor on deck twelve\n"
                "is REALLY hot. Suspiciously hot. I have personally been winked\n"
                "at by her in a way that violates several Newton-grade physical\n"
                "laws. I am not SAYING. I am just SAYING.'\n\n"
                "ROSLIN (stage whisper): 'NO.'"
            ),
            "delta": {"credibility": -8, "suspicion": 10, "cylon_vibes": 5, "morale": 3},
        },
        "political": {
            "text": (
                "You say: 'Cylon infiltration is, the President assures us, an\n"
                "active matter under continuous review by qualified specialists.\n"
                "I am not, technically, one of those specialists.'\n\n"
                "ROSLIN (stage whisper): 'Acceptable. Continue.'"
            ),
            "delta": {"credibility": 7, "morale": -3},
        },
        "unhinged_text": (
            "You say: 'YES. Yes, there are Cylons in this room. Right now. At\n"
            "least one of them is — one of them is me. I'm KIDDING. I'm kidding,\n"
            "right? Frak. Frak frak frak.'\n"
        ),
        "unhinged_outcomes": [
            {
                "credibility": 20, "morale": 8,
                "note": ("The room laughs. The room LAUGHS. The laughter is, you\n"
                         "note, real. The laughter is, also, slightly nervous.\n"
                         "ROSLIN (stage whisper): 'Specialist that was actually the\n"
                         "right play how did you DO that.'"),
            },
            {
                "credibility": -25, "suspicion": 12,
                "note": ("Three reporters stand up. Two of them leave. One of\n"
                         "them writes furiously and underlines the word YOU.\n"
                         "ROSLIN (stage whisper): 'You are on your OWN now.'"),
            },
        ],
    },
    {
        "id": "new_caprica",
        # Parody: the New Caprica settlement arc
        "question": (
            "REPORTER (Refugee Quarterly): 'Sources tell us the fleet is\n"
            "considering permanent civilian settlement on the next habitable\n"
            "planet. Some pilots are reportedly drawing up land claims already.'"
        ),
        "honest": {
            "text": (
                "You say: 'I can confirm that Captain Apollo has been brooding\n"
                "into a porthole. I cannot confirm anything else. The brooding is,\n"
                "by my count, eight hours a day. That is all I have.'\n\n"
                "ROSLIN (stage whisper): 'Why are you like this.'"
            ),
            "delta": {"credibility": 5, "suspicion": 3, "morale": 2},
        },
        "political": {
            "text": (
                "You say: 'Permanent settlement options remain part of the fleet's\n"
                "long-term strategic planning. Specific decisions rest with the\n"
                "Admiral and the President. I am, again, a specialist.'\n\n"
                "ROSLIN (stage whisper): 'Good. Boring. Excellent.'"
            ),
            "delta": {"credibility": 7, "morale": -3},
        },
        "unhinged_text": (
            "You say: 'I support settlement. I want a yard. I want a yard with a\n"
            "dog. The dog will be named Captain Frakkin' Adorable. He is already,\n"
            "technically, in a small picture frame in my locker. I will be\n"
            "bringing him with me. The dog has waited LONG ENOUGH.'\n"
        ),
        "unhinged_outcomes": [
            {
                "credibility": 15, "morale": 12,
                "note": ("A Quorum delegate cries openly. Several reporters cry\n"
                         "less openly. The press conference, briefly, becomes\n"
                         "about a dog. ROSLIN (stage whisper): 'Use this. Use\n"
                         "this EVERY time.'"),
            },
            {
                "credibility": -10, "morale": 6,
                "note": ("A reporter asks for the dog's full name and ranks. You\n"
                         "give them. Roslin's eye is, you note, twitching."),
            },
        ],
    },
    {
        "id": "tigh_drinking",
        # Parody: Tigh's chronic alcoholism, never officially acknowledged
        "question": (
            "REPORTER (Galactica Times — yes, internal): 'There are unconfirmed\n"
            "reports that Colonel Tigh has been... unavailable... during recent\n"
            "operational events. Care to comment?'"
        ),
        "honest": {
            "text": (
                "You say: 'The XO has been in a toilet stall for nine consecutive\n"
                "watches. He keeps a flask under a loose tile. He hums the Colonial\n"
                "Anthem off-key. He may have other flasks. I have personally\n"
                "returned three of them to him.'\n\n"
                "ROSLIN (stage whisper): 'I am going to space you. I am going to\n"
                "space you MYSELF.'"
            ),
            "delta": {"credibility": -15, "suspicion": 12, "morale": 4},
        },
        "political": {
            "text": (
                "You say: 'Colonel Tigh has been ensuring deck-level operational\n"
                "readiness through direct, unconventional inspection methods. The\n"
                "Colonel's deployment is at the Admiral's discretion.'\n\n"
                "ROSLIN (stage whisper): 'Beautiful. BEAUTIFUL.'"
            ),
            "delta": {"credibility": 10, "morale": -4},
        },
        "unhinged_text": (
            "You say: 'Colonel Tigh is a haunted brewery in a flight suit and I\n"
            "will not, under oath, on the record, or under torture, say otherwise.'\n"
        ),
        "unhinged_outcomes": [
            {
                "credibility": 16, "morale": 10,
                "note": ("Every single reporter writes down the phrase 'haunted\n"
                         "brewery in a flight suit.' The phrase will appear on\n"
                         "three different morning broadcasts. ROSLIN (stage\n"
                         "whisper): 'I — I am not sure if you are a genius.'"),
            },
            {
                "credibility": -22, "suspicion": 9,
                "note": ("Three reporters look at each other. One of them mouths\n"
                         "'we got him.' ROSLIN (stage whisper): 'You have just,\n"
                         "specifically, gotten the XO. Congratulations.'"),
            },
        ],
    },
    {
        "id": "mystery_meat",
        # Parody: the persistent food/resource scarcity arc
        "question": (
            "REPORTER (Civilian Affairs): 'Specialist, the quartermaster has\n"
            "refused all comment on rationing protocols. Civilian morale around\n"
            "food allocation is reportedly poor. What can you tell us about the\n"
            "fleet's nutritional logistics?'"
        ),
        "honest": {
            "text": (
                "You say: 'The protein vat in the mess hall has been the same vat\n"
                "since the Second Cylon War. The vat absorbs whatever falls in it.\n"
                "I have personally identified, in the vat, a piece of regulation\n"
                "deck plate and a rat skeleton. I have also identified the dog\n"
                "tags of one Crewman Engram. Crewman Engram was reported transferred\n"
                "three years ago.'\n\n"
                "ROSLIN (stage whisper): 'STOP. STOP. STOPSTOPSTOP—'"
            ),
            "delta": {"credibility": -18, "suspicion": 15, "morale": 5},
        },
        "political": {
            "text": (
                "You say: 'Logistical adjustments are made on a continuous basis\n"
                "to maintain fleet wellbeing. The quartermaster's office is best\n"
                "positioned to address specific allocation questions.'\n\n"
                "ROSLIN (stage whisper): 'Yes. YES.'"
            ),
            "delta": {"credibility": 8, "morale": -4},
        },
        "unhinged_text": (
            "You say: 'The Cook is one of the Cylons. I'm almost certain. Look\n"
            "at the eyes. The vat is ALSO one of the Cylons. The vat is, on\n"
            "balance, the better officer.'\n"
        ),
        "unhinged_outcomes": [
            {
                "credibility": 14, "morale": 9, "cylon_vibes": 4,
                "note": ("A reporter writes: 'Specialist endorses talking algae.'\n"
                         "The headline writes itself. ROSLIN (stage whisper): 'I\n"
                         "cannot believe that worked.'"),
            },
            {
                "credibility": -18, "suspicion": 11,
                "note": ("The room goes quiet. A delegate from Aerelon walks out.\n"
                         "ROSLIN (stage whisper): 'You are SO MUCH worse than\n"
                         "Tigh would have been.'"),
            },
        ],
    },
]


# ─── runtime helpers ─────────────────────────────────────────────────────────


def _question_rng(world, question_id: str) -> random.Random:
    """Per-(player, day, question) seeded RNG so unhinged outcomes are
    deterministic per save state (and tests can predict them by fixing
    player_name + day)."""
    seed = f"press:{world.player_name or 'anon'}:{world.day}:{question_id}"
    return random.Random(seed)


def _apply_delta(world, delta: dict) -> None:
    """Apply a stat-delta dict to the world. Keys: credibility, morale,
    suspicion, cylon_vibes."""
    if "credibility" in delta:
        cur = world.flags.get("press_credibility", 50)
        new = max(0, min(100, cur + delta["credibility"]))
        world.flags["press_credibility"] = new
    if "morale" in delta:
        bump_stat(world, "morale", delta["morale"])
    if "suspicion" in delta:
        bump_stat(world, "suspicion", delta["suspicion"])
    if "cylon_vibes" in delta:
        bump_stat(world, "cylon_vibes", delta["cylon_vibes"])


def _current_question(world) -> dict | None:
    qid = world.flags.get("press_questions", [None] * 6)
    idx = world.flags.get("press_round", 0)
    if idx >= len(qid):
        return None
    q_id = qid[idx]
    for q in QUESTIONS:
        if q["id"] == q_id:
            return q
    return None


def _render_question(question: dict, round_index: int, total: int) -> str:
    """Format the question + the three response prompts."""
    return (
        f"── Round {round_index + 1} of {total} ──\n\n"
        f"{question['question']}\n\n"
        f"You can answer: honest, political, or unhinged."
    )


# ─── entry ────────────────────────────────────────────────────────────────────


def start_press_conference(world) -> str:
    """Roslin shoves the player in front of the press. Sets the flags and
    returns the opening narrative + first question."""
    # Already in progress? Don't restart.
    if world.flags.get("press_active"):
        q = _current_question(world)
        if q:
            return _render_question(q, world.flags["press_round"],
                                    len(world.flags.get("press_questions", [])))
        return ""

    # Pick 6 questions (all of them, in pool order) — deterministic per session.
    selected = [q["id"] for q in QUESTIONS]
    world.flags["press_active"] = True
    world.flags["press_round"] = 0
    world.flags["press_questions"] = selected
    world.flags["press_credibility"] = 50

    opening = (
        "She looks at you. She looks at her watch. She looks at the doorway\n"
        "behind you, where two assistants are, you note, BLOCKING the doorway.\n"
        "She looks back at you. She has, you note, made a decision.\n\n"
        "ROSLIN: 'Specialist. The Quorum has called an emergency briefing. The\n"
        "Admiral is indisposed. The XO is indisposed WITH the Admiral, in a way\n"
        "I will not elaborate on. Doctor Baltar is having an intense personal\n"
        "exchange with no one in his lab. That leaves YOU.'\n\n"
        "She pulls you up by the elbow with a strength a dying woman should not,\n"
        "by any reasonable physiology, possess.\n\n"
        "ROSLIN (briefing you on the move, fast and clipped): 'Three rules.\n"
        "One — say NOTHING true. Two — say NOTHING false. Three — say NOTHING.\n"
        "Each question, you have three options: HONEST, POLITICAL, or UNHINGED.\n"
        "Pick honest if you are tired of living. Pick political if you are tired\n"
        "of having a soul. Pick unhinged if you have, frankly, no further plan.'\n\n"
        "She pushes you through a door into a room full of press. Lights. Cameras.\n"
        "Reporters. A small podium. A glass of water. The water is yours. The\n"
        "podium is yours. The press is, briefly and unhappily, yours.\n\n"
        "ROSLIN (stage whisper from your six): 'GO.'\n\n"
    )

    first_question = _render_question(QUESTIONS[0], 0, len(selected))
    return opening + first_question


# ─── per-round input handling ────────────────────────────────────────────────


def handle_input(world, raw: str) -> HandlerResult:
    """Called by the session loop when press_active is True. Parses the
    player's response category, applies the round's effects, prints the
    next question (or the final outcome), and returns a HandlerResult.

    Recognized inputs:
        honest / true / truth
        political / spin / safe
        unhinged / chaos / wild
        quit                — fall back to normal quit handling

    Anything unrecognized re-prompts the current question."""
    lower = raw.strip().lower()

    # Let the player quit out — but DO NOT tear down press state. The
    # autosave on quit captures the mid-conference snapshot so the player
    # can reload and resume on the same round.
    if lower in ("quit", "exit", "q"):
        return HandlerResult(text="Frak out, specialist.", quit=True, advance_turn=False)

    # Determine category.
    if any(t in lower for t in ("honest", "true", "truth")):
        category = "honest"
    elif any(t in lower for t in ("polit", "spin", "safe", "non-answer")):
        category = "political"
    elif any(t in lower for t in ("unhing", "chaos", "wild", "off-script", "off script")):
        category = "unhinged"
    else:
        q = _current_question(world)
        if q is None:
            # Defensive: press state corrupted; bail out.
            _clear_press_state(world)
            return HandlerResult(
                text="(The press conference, somehow, has ended. You shuffle off.)",
                advance_turn=False,
            )
        return HandlerResult(
            text="Pick: honest, political, or unhinged.\n\n" +
                 _render_question(q, world.flags["press_round"],
                                  len(world.flags["press_questions"])),
            advance_turn=False,
        )

    q = _current_question(world)
    if q is None:
        _clear_press_state(world)
        return HandlerResult(text="(The press conference ends abruptly.)",
                              advance_turn=False)

    # Apply the chosen response.
    parts: list[str] = []
    if category == "honest":
        parts.append(q["honest"]["text"])
        _apply_delta(world, q["honest"]["delta"])
    elif category == "political":
        parts.append(q["political"]["text"])
        _apply_delta(world, q["political"]["delta"])
    else:  # unhinged
        rng = _question_rng(world, q["id"])
        outcome = rng.choice(q["unhinged_outcomes"])
        parts.append(q["unhinged_text"])
        parts.append(outcome["note"])
        _apply_delta(world, {k: v for k, v in outcome.items() if k != "note"})

    # Advance to next round.
    world.flags["press_round"] += 1
    next_q = _current_question(world)
    if next_q is None:
        # Conference is over. Evaluate outcome and clean up.
        parts.append(_finalize(world))
        _clear_press_state(world)
    else:
        parts.append(_render_question(next_q, world.flags["press_round"],
                                      len(world.flags["press_questions"])))

    return HandlerResult(text="\n\n".join(parts), advance_turn=False)


# ─── outcome evaluation ──────────────────────────────────────────────────────


HIGH_THRESHOLD = 70
LOW_THRESHOLD = 30
ROCK_BOTTOM = 10


def _finalize(world) -> str:
    """End the press conference and apply outcome consequences."""
    cred = world.flags.get("press_credibility", 50)

    if cred <= ROCK_BOTTOM:
        # Rock bottom: briefly famous. Big stat consequences and a future-hook flag.
        bump_stat(world, "morale", -10)
        bump_stat(world, "suspicion", 25)
        world.flags["was_briefly_famous"] = True
        world.flags["press_outcome"] = "rock_bottom"
        return (
            "ROSLIN (stage whisper, devastated): 'Specialist. SPECIALIST. What\n"
            "have you DONE.'\n\n"
            "The press conference does not end so much as collapse. Reporters\n"
            "scramble. Cameras dolly out. Three different journalists try to ask\n"
            "you for follow-up interviews. One of them has, somehow, your full\n"
            "name and rank, which is more than anyone aboard this ship has had in\n"
            "MONTHS.\n\n"
            "By tomorrow morning, your face will be on every broadcast in the\n"
            "fleet. By tomorrow afternoon, somebody will be selling a T-shirt\n"
            "with your most quotable line on it. By tomorrow night, somebody\n"
            "with a high security clearance will be very, very interested in you.\n\n"
            "You are, briefly, famous. This is, on balance, the worst thing that\n"
            "has happened to you all week. And you've had a week."
        )

    if cred <= LOW_THRESHOLD:
        # Low: accidentally confirmed something explosive
        bump_stat(world, "suspicion", 30)
        world.flags["press_outcome"] = "low"
        world.flags["press_confirmed_conspiracies"] = True
        return (
            "ROSLIN (stage whisper): 'That. Could have gone. Better.'\n\n"
            "The press conference ends. The press files out. Three reporters file\n"
            "out FAST. By the time you return to your bunk, the entire fleet has\n"
            "heard about the XO's flask, the protein vat, and the woman in the\n"
            "brig — sometimes all three in the same paragraph. Suspicion, ship-\n"
            "wide, climbs.\n\n"
            "Hadrian, when you get back to env_control, looks at you for a long\n"
            "moment and just says: 'oh, frak. Oh, frak no, specialist. Oh, no.'"
        )

    if cred >= HIGH_THRESHOLD:
        # High: Roslin impressed; reward
        bump_stat(world, "morale", 10)
        bump_stat(world, "suspicion", -5)
        world.flags["press_outcome"] = "high"
        move_item_to_inventory(world, "commendation_letter")
        return (
            "ROSLIN (no longer whispering): 'Specialist. That was — that was\n"
            "frankly an upset. I had drafted a resignation letter while we walked\n"
            "in here. I had it in my POCKET. I had IT IN MY POCKET.'\n\n"
            "She hands you a folded sheet of presidential letterhead. Her\n"
            "handwriting is clean. Your name is on it. Your name is, you note,\n"
            "MISSPELLED. By two letters. In a way that suggests she heard the\n"
            "name approximately and was about to use the wrong one but didn't,\n"
            "in time, get THERE.\n\n"
            "ROSLIN: 'Take this. Show it to anyone who asks. Don't show it to\n"
            "anyone who doesn't. You did well today, specialist...' She squints\n"
            "at the letter. She squints at you. She forgets your name in real\n"
            "time. '...specialist. Yes. Good work.'\n\n"
            "(You received: presidential commendation letter.)"
        )

    # Medium: no special outcome
    world.flags["press_outcome"] = "medium"
    return (
        "ROSLIN (stage whisper): 'That was — that was something, specialist.\n"
        "Not the something we needed. But A something. We will take it.'\n\n"
        "The press conference ends. You exit. The water glass remains, untouched."
    )


def _clear_press_state(world) -> None:
    """Tear down all per-conference flags so a future invocation starts clean."""
    for k in ("press_active", "press_round", "press_questions",
              "press_credibility"):
        world.flags.pop(k, None)


# ─── exposed predicate ───────────────────────────────────────────────────────


def is_active(world) -> bool:
    return bool(world.flags.get("press_active"))
