"""Parser: text in, structured Command out. Dumb on purpose."""

from dataclasses import dataclass
from typing import Optional

ARTICLES = {"the", "a", "an", "some", "my", "your"}

DIRECTIONS = {
    "n": "north", "north": "north",
    "s": "south", "south": "south",
    "e": "east", "east": "east",
    "w": "west", "west": "west",
    "u": "up", "up": "up",
    "d": "down", "down": "down",
    "in": "in", "out": "out",
}

VERB_SYNONYMS = {
    "look": "look", "l": "look",
    "examine": "examine", "x": "examine", "inspect": "examine", "check": "examine", "read": "examine",
    "go": "go", "move": "go", "walk": "go", "head": "go",
    "take": "take", "get": "take", "grab": "take", "pick": "take",
    "drop": "drop", "leave": "drop", "discard": "drop",
    "use": "use",
    "give": "give", "hand": "give",
    "talk": "talk", "speak": "talk", "ask": "talk",
    "inventory": "inventory", "i": "inventory", "inv": "inventory",
    "wait": "wait", "z": "wait",
    "sleep": "sleep", "rest": "sleep", "nap": "sleep",
    "save": "save",
    "load": "load", "restore": "load",
    "help": "help", "?": "help",
    "hint": "hint", "hints": "hint", "stuck": "hint", "advice": "hint",
    "quit": "quit", "exit": "quit", "q": "quit",
    "salute": "salute",
    "status": "status", "stat": "status", "stats": "status", "vibe": "status", "vibes": "status",
    "frak": "frak", "frack": "frak", "fuck": "frak", "shit": "frak", "damn": "frak",
    "drink": "drink", "sip": "drink", "chug": "drink",
    "eat": "eat", "bite": "eat",
}

# Direction tokens also work as a "go" verb on their own
for _d in list(DIRECTIONS.keys()):
    VERB_SYNONYMS.setdefault(_d, "go")

VERB_PREPOSITIONS: dict[str, list[str]] = {
    "use": ["on", "with"],
    "give": ["to"],
    "talk": ["about"],
    "go": [],
}

# Connectors that get stripped from the front of a noun phrase if not consumed as a splitter
LEADING_CONNECTORS = {"to", "at", "with", "into", "onto"}


@dataclass
class Command:
    verb: Optional[str]
    obj: Optional[str] = None
    target: Optional[str] = None
    raw: str = ""
    error: Optional[str] = None  # parse-level error (unknown verb, empty input)


def _normalize(raw: str) -> list[str]:
    out = []
    buf = []
    for ch in raw.lower():
        if ch.isalnum() or ch in "'_":
            buf.append(ch)
        else:
            if buf:
                out.append("".join(buf))
                buf = []
    if buf:
        out.append("".join(buf))
    return out


def _strip_articles(tokens: list[str]) -> list[str]:
    return [t for t in tokens if t not in ARTICLES]


def _strip_leading_connectors(tokens: list[str]) -> list[str]:
    while tokens and tokens[0] in LEADING_CONNECTORS:
        tokens = tokens[1:]
    return tokens


def parse(raw: str) -> Command:
    raw = raw.strip()
    if not raw:
        return Command(verb=None, raw=raw, error="empty")

    tokens = _normalize(raw)
    if not tokens:
        return Command(verb=None, raw=raw, error="empty")

    tokens = _strip_articles(tokens)
    if not tokens:
        return Command(verb=None, raw=raw, error="empty")

    # Single-token direction → "go <dir>"
    if len(tokens) == 1 and tokens[0] in DIRECTIONS:
        return Command(verb="go", obj=DIRECTIONS[tokens[0]], raw=raw)

    head = tokens[0]
    if head not in VERB_SYNONYMS:
        return Command(verb=None, raw=raw, error="unknown_verb")

    verb = VERB_SYNONYMS[head]
    rest = tokens[1:]

    # Normalize direction tokens in the rest for "go" verb
    if verb == "go" and rest:
        rest = _strip_leading_connectors(rest)
        if rest and rest[0] in DIRECTIONS:
            rest[0] = DIRECTIONS[rest[0]]

    # Split on verb-specific preposition if any
    prepositions = VERB_PREPOSITIONS.get(verb, [])
    obj_tokens, target_tokens = rest, []
    if prepositions:
        for i, tok in enumerate(rest):
            if tok in prepositions:
                obj_tokens = rest[:i]
                target_tokens = rest[i + 1:]
                break

    obj_tokens = _strip_leading_connectors(obj_tokens)
    target_tokens = _strip_leading_connectors(target_tokens)

    obj = " ".join(obj_tokens) if obj_tokens else None
    target = " ".join(target_tokens) if target_tokens else None

    return Command(verb=verb, obj=obj, target=target, raw=raw)
