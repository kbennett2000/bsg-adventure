"""Persistent achievements, written to disk per-player.

File location: <BSG_SAVE_DIR>/<player>/achievements.json
"""

import json
from pathlib import Path

from engine import save as save_module
from engine.world import get_stat


# Each achievement: id → {name, desc, check(world) → bool}
ACHIEVEMENTS = {
    "so_say_we_all": {
        "name": "So Say We All",
        "desc": "Said 'frak' 50 times in one shift.",
        "check": lambda w: w.flags.get("__frak_index__", 0) >= 50,
    },
    "lahey_coded": {
        "name": "Lahey-coded",
        "desc": "Drank with Tigh five times. (Or, drank from one of his bottles five times. Tigh was, at the time, present in spirit.)",
        "check": lambda w: w.flags.get("tigh_drink_count", 0) >= 5,
    },
    "toaster_lover": {
        "name": "Toaster Lover",
        "desc": "Romanced two different Sixes simultaneously.",
        "check": lambda w: w.flags.get("__ended__") == "cylon_love_triangle",
    },
    "promotion_material": {
        "name": "Promotion Material",
        "desc": "Completed a run with SUSPICION at 0. (Impossible without trying. Compliments, specialist.)",
        "check": lambda w: w.flags.get("__ended__") is not None and get_stat(w, "suspicion") == 0,
    },
    "all_of_this_has_happened_before": {
        "name": "All of This Has Happened Before",
        "desc": "Finished a new-game-plus run.",
        "check": lambda w: w.flags.get("__ended__") is not None and bool(w.flags.get("ng_plus")),
    },
}


def _achievements_path(player_name: str) -> Path:
    """Where this player's achievements file lives."""
    if not save_module.is_safe_name(player_name):
        raise ValueError(f"invalid player name: {player_name!r}")
    return save_module.save_root() / player_name / "achievements.json"


def load_unlocked(player_name: str) -> set[str]:
    try:
        p = _achievements_path(player_name)
    except ValueError:
        return set()
    if not p.exists():
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return set(data)
        if isinstance(data, dict):
            return set(data.get("unlocked", []))
    except Exception:
        return set()
    return set()


def save_unlocked(player_name: str, unlocked: set[str]) -> None:
    p = _achievements_path(player_name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sorted(unlocked), indent=2), encoding="utf-8")


def check_and_unlock(world) -> list[dict]:
    """Evaluate all achievement predicates. Persist newly unlocked ones.

    Returns the list of newly-unlocked achievement records (for display)."""
    name = world.player_name
    if not name:
        return []
    try:
        already = load_unlocked(name)
    except Exception:
        return []
    newly = []
    for aid, ach in ACHIEVEMENTS.items():
        if aid in already:
            continue
        try:
            if ach["check"](world):
                already.add(aid)
                newly.append({"id": aid, "name": ach["name"], "desc": ach["desc"]})
        except Exception:
            continue
    if newly:
        try:
            save_unlocked(name, already)
        except Exception:
            pass
    return newly


def render_unlock_banner(achievement: dict) -> str:
    return (
        f"  *** ACHIEVEMENT UNLOCKED: {achievement['name']} ***\n"
        f"      {achievement['desc']}"
    )
