"""NPC schedules — where each character is during each watch.

Each entry maps `shift_index → room_id`. Shifts are indexed by
`engine.world.SHIFT_NAMES`:

    0 = Morning Watch
    1 = Forenoon
    2 = Afternoon
    3 = Dog Watch
    4 = Night

NPCs with a schedule entry are present in the listed room AT THAT SHIFT
and NOT elsewhere. NPCs without a schedule entry stay at their static
room-list placement (the legacy behavior). To suppress an NPC entirely
during a given shift, omit that shift from the schedule.
"""

# Senior officer schedules (user-spec'd):
SCHEDULES: dict[str, dict[int, str]] = {
    "tigh": {
        0: "head_deck_5",   # always in the head — increasingly drunk as day goes on
        1: "head_deck_5",
        2: "head_deck_5",
        3: "head_deck_5",
        4: "head_deck_5",   # passed out at Night — stash is findable
    },
    "starbuck": {
        0: "pilots_rec",    # face-down on the triad table
        1: "pilots_rec",
        2: "pilots_rec",    # cards-night IS afternoon
        3: "pilots_rec",
        4: "brig",          # in the brig, again
    },
    "adama": {
        0: "cic",
        1: "cic",           # canonical "Adama at the plot, Forenoon"
        2: "cic",
        3: "cic",
        4: "adamas_quarters",
    },
    "baltar": {
        0: "baltars_lab",   # always in the lab, regardless of hour
        1: "baltars_lab",
        2: "baltars_lab",
        3: "baltars_lab",
        4: "baltars_lab",
    },
    # Other NPCs — sensible defaults so the world doesn't feel inconsistent:
    "apollo": {
        0: "pilots_rec",
        1: "pilots_rec",
        2: "pilots_rec",
        3: "pilots_rec",
        4: "observation_deck",   # brooding at night
    },
    "cook": {
        0: "mess_hall",          # mess open
        1: "mess_hall",          # technically not open per the spec but cook is on prep
        2: "mess_hall",          # mess open
        3: "mess_hall",          # cook on cleanup
        # 4 (Night): cook gone — kitchen unattended, stash bottle in there is grabbable
    },
}


def npc_room_at_shift(npc_id: str, shift: int) -> str | None:
    """Where is this NPC right now? Returns None if the NPC has no schedule
    entry for this shift (means: suppress from the world this shift)."""
    schedule = SCHEDULES.get(npc_id)
    if schedule is None:
        return None
    return schedule.get(shift)


def npcs_scheduled_for(room_id: str, shift: int) -> list[str]:
    """Which scheduled NPCs are in `room_id` right now."""
    return [
        npc_id
        for npc_id, schedule in SCHEDULES.items()
        if schedule.get(shift) == room_id
    ]


def has_schedule(npc_id: str) -> bool:
    return npc_id in SCHEDULES


# Tigh drunkenness escalates across the day. Used by his dialogue.
TIGH_DRUNK_LEVEL = {
    0: "buzzed",        # Morning Watch
    1: "buzzed",        # Forenoon
    2: "slurring",      # Afternoon
    3: "drunk",         # Dog Watch
    4: "passed_out",    # Night — silent, just snoring
}


def tigh_state(shift: int) -> str:
    return TIGH_DRUNK_LEVEL.get(shift, "buzzed")
