"""Daily duty roster.

Each shipboard day the player is assigned one chore, picked deterministically
from the duty pool based on the day number. The chore is posted in Corridor
C-12 ("examine roster"). Completing it: small morale hit (chores are boring)
but a suspicion reduction (you look like a model specialist). Skipping it: a
suspicion bump at the next day rollover.

This module also owns the hunger mechanic — the mess is open Morning Watch
and Afternoon; missing a meal raises exhaustion at the next day rollover.
"""

import random

from engine.world import bump_stat, get_stat


# A chore = (id, roster_line, completion_check, narrative_on_completion).
# `completion_check(world)` returns True if the chore has been performed today.
# `narrative_on_completion` is text appended on successful completion.

# Each chore key maps to a record. Random selection happens by index modulo
# the keys list, seeded by `(day, player_name)` for determinism per save.

CHORE_DEFS: dict[str, dict] = {
    "mop_the_head": {
        "roster_line": (
            "  • SPECIALIST: report to the DECK 5 HEAD and MOP THE FRAKKIN' DECK.\n"
            "    (Tigh's deck. He's particular about the tile.)"
        ),
        "check": lambda w: w.flags.get("duty_mopped_today", False),
        "completion": (
            "You mop the head. The mop, somehow, comes back dirtier than it went in.\n"
            "Tigh, in the middle stall, says 'better, son' through the partition\n"
            "without breaking the rhythm of his humming."
        ),
    },
    "reroute_coolant": {
        "roster_line": (
            "  • SPECIALIST: REROUTE COOLANT, deck 5 environmental.\n"
            "    Schematic on console. Console blinks. Console always blinks."
        ),
        "check": lambda w: w.flags.get("duty_console_today", False),
        "completion": (
            "You reroute the coolant. The console blinks. The console keeps blinking.\n"
            "It will blink again tomorrow. The blinking is the only constant. It will\n"
            "outlive you. It will outlive Tigh. It will outlive the war."
        ),
    },
    "escort_prisoner": {
        "roster_line": (
            "  • SPECIALIST: STANDBY ESCORT, brig. Stand near the cell. Look\n"
            "    UNINTIMIDATED. Do not, repeat NOT, MAKE EYE CONTACT."
        ),
        "check": lambda w: w.flags.get("duty_brig_today", False),
        "completion": (
            "You stand outside the cell for the regulation forty minutes. The prisoner\n"
            "in red smiles at you the entire time. You make eye contact for, by your\n"
            "own count, nine of those minutes. You suspect this is your fault."
        ),
    },
    "assist_baltar": {
        "roster_line": (
            "  • SPECIALIST: \"ASSIST\" DR. BALTAR, lab. Don't ask questions.\n"
            "    Don't answer questions. Don't look at the chair."
        ),
        "check": lambda w: w.flags.get("duty_baltar_today", False),
        "completion": (
            "You stand in Baltar's lab while he talks to no one for two hours. He\n"
            "occasionally turns and addresses you with technical questions that you\n"
            "do not understand and that, on review, do not appear to be questions.\n"
            "You leave when he says 'thank you, that was VERY illuminating' to the\n"
            "empty chair."
        ),
    },
}


CHORE_IDS = sorted(CHORE_DEFS.keys())


# ─── duty-of-the-day selection ─────────────────────────────────────────────────


def _pick_duty_for_day(world) -> str:
    """Deterministically pick today's chore from (day, player_name). Saves
    must round-trip the same assignment after a load. Seed is a STRING so
    `random.Random` accepts it AND the seeding is stable across processes
    (Python's `hash` is salted per-process and would not survive save/load)."""
    seed = f"{world.day}:{world.player_name or 'anon'}"
    rng = random.Random(seed)
    return rng.choice(CHORE_IDS)


def current_duty(world) -> str:
    """Return today's duty id. Stored in flags so we don't re-roll mid-day."""
    stored = world.flags.get("duty_today")
    if stored in CHORE_DEFS:
        return stored
    duty = _pick_duty_for_day(world)
    world.flags["duty_today"] = duty
    return duty


def render_roster_text(world) -> str:
    """The text the player sees when examining the corridor C-12 roster."""
    duty_id = current_duty(world)
    chore = CHORE_DEFS[duty_id]
    done = chore["check"](world)
    status = "[COMPLETED]" if done else "[OUTSTANDING]"
    header = (
        f"  DAILY DUTY ROSTER  —  Day {world.day}, {_shift_label(world)}\n"
        f"  {'-' * 48}"
    )
    body = chore["roster_line"]
    footer = f"\n  Status: {status}"
    return f"{header}\n{body}{footer}"


def _shift_label(world) -> str:
    from engine.world import SHIFT_NAMES
    return SHIFT_NAMES[world.shift % len(SHIFT_NAMES)]


# ─── completion hooks ─────────────────────────────────────────────────────────

def _try_complete(world, chore_id: str, flag_name: str) -> str | None:
    """Called by action handlers to mark a chore done. If today's duty
    matches, return the completion narrative (and apply the rewards)."""
    if world.flags.get(flag_name):
        return None  # already done today
    world.flags[flag_name] = True
    duty = current_duty(world)
    if duty != chore_id:
        return None  # action performed but it wasn't today's duty
    # Reward: boring but exonerating
    bump_stat(world, "morale", -3)
    bump_stat(world, "suspicion", -5)
    return CHORE_DEFS[chore_id]["completion"]


def on_mop_head(world) -> str | None:
    """Hook: player just used mop in the head."""
    return _try_complete(world, "mop_the_head", "duty_mopped_today")


def on_reroute_coolant(world) -> str | None:
    """Hook: player just used the env_control console."""
    return _try_complete(world, "reroute_coolant", "duty_console_today")


def on_brig_escort(world) -> str | None:
    """Hook: player examined the cell in the brig."""
    return _try_complete(world, "escort_prisoner", "duty_brig_today")


def on_baltar_assist(world) -> str | None:
    """Hook: player talked to Baltar in his lab."""
    return _try_complete(world, "assist_baltar", "duty_baltar_today")


# ─── shift-change hook ────────────────────────────────────────────────────────


def on_shift_change(world) -> str | None:
    """Called by the session when a shift advance happens. Handles:
       1) End-of-day duty rollover (after a Night → Morning Watch transition)
       2) End-of-day hunger penalty
    Returns optional narrative text to display.

    If multiple days have elapsed since the last rollover (e.g. the player
    used `sleep` repeatedly, or a Cylon resurrection bumped the calendar),
    we apply ONE penalty per missed day rather than collapsing them all to
    a single hit — otherwise blasting forward through the calendar would be
    a free way to dodge consequences."""
    # Day rollover detection: turns_this_shift was just reset to 0 by the
    # advance, so we instead use a separate sentinel — `_last_rollover_day`.
    # If the current day > the last rollover day, we just crossed a day boundary.
    last_rollover = world.flags.get("_last_rollover_day", world.day)
    if world.day == last_rollover and not world.flags.get("_first_shift_change_done"):
        # First shift change ever — just initialize without penalty.
        world.flags["_first_shift_change_done"] = True
        world.flags["_last_rollover_day"] = world.day
        return None
    missed_days = world.day - last_rollover
    if missed_days <= 0:
        return None  # same day still; no rollover work

    # Day(s) rolled over. Evaluate every missed day. Day 1 uses real flags
    # (the player may have completed duty / eaten on the most recent day
    # they were conscious); days 2..N assume nothing was done (the player
    # skipped past those days entirely).
    total_duty_penalty = 0
    total_hunger_penalty = 0

    yesterday_duty = world.flags.get("duty_today")
    duty_done_yesterday = (
        yesterday_duty in CHORE_DEFS
        and CHORE_DEFS[yesterday_duty]["check"](world)
    )
    if yesterday_duty in CHORE_DEFS and not duty_done_yesterday:
        total_duty_penalty += 5
    if not world.flags.get("ate_today"):
        total_hunger_penalty += 6

    extra_missed = missed_days - 1
    if extra_missed > 0:
        total_duty_penalty += 5 * extra_missed
        total_hunger_penalty += 6 * extra_missed

    narratives: list[str] = []
    if total_duty_penalty:
        bump_stat(world, "suspicion", total_duty_penalty)
        if missed_days > 1:
            narratives.append(
                "Word on the deck: you've been unreliable about your duties.\n"
                "Several people notice. Several people always notice."
            )
        else:
            narratives.append(
                "Word on the deck: you skipped your assigned duty yesterday.\n"
                "Someone notices. Someone always notices."
            )
    if total_hunger_penalty:
        bump_stat(world, "exhaustion", total_hunger_penalty)
        if missed_days > 1:
            narratives.append(
                "You have not, in the end, eaten in days. Your stomach has,\n"
                "now, several opinions about this. They are all loud."
            )
        else:
            narratives.append(
                "You did not, in the end, eat anything yesterday. Your stomach has,\n"
                "now, an opinion on this. Your stomach is being VOCAL about it."
            )
    # Reset per-day flags and rotate to today's duty.
    for k in (
        "duty_today", "duty_mopped_today", "duty_console_today",
        "duty_brig_today", "duty_baltar_today", "ate_today",
    ):
        world.flags.pop(k, None)
    world.flags["_last_rollover_day"] = world.day
    # Force today's duty to be picked (so render_roster_text is deterministic).
    current_duty(world)
    if narratives:
        return "\n\n".join(narratives)
    return None
