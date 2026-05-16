"""Ambient turn-end events. Content registers strings (or callables); the session
loop calls tick() after each successful turn and prints whatever comes back.

The probability and the strings themselves come from content/flavor.py at import
time — the engine just runs the dice and dispatch."""

import random
from typing import Callable, Union

AmbientEntry = Union[str, Callable]  # str (printed verbatim) or callable(world) → str|None

_REGISTERED: list[AmbientEntry] = []
_PROBABILITY = 0.18  # ~1 in 5 turns


def register_ambient(*entries: AmbientEntry) -> None:
    _REGISTERED.extend(entries)


def set_probability(p: float) -> None:
    global _PROBABILITY
    _PROBABILITY = p


def tick(world) -> str | None:
    """Roll the dice and possibly return an ambient flavor line for this turn."""
    if not _REGISTERED:
        return None
    if random.random() >= _PROBABILITY:
        return None
    entry = random.choice(_REGISTERED)
    if callable(entry):
        return entry(world)
    return entry


def reset() -> None:
    """Test-only: clear ambient registrations."""
    _REGISTERED.clear()
