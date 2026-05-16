"""Entry point for local play."""

import random
import sys

import content  # noqa: F401  — triggers all content registration
from engine.io import LocalIO
from engine.save import is_safe_name
from engine.session import Session
from engine.world import new_world


TITLE_ART = r"""
                      _______________
                     /               \_____
                    /                     \____
            _______/                          \________
           /                                          \
          [    B A T T L E S T A R   G A L A C T I C A  ]
           \_____      __________________      _______/
                 \____/                  \____/
                  ||||                    ||||
                  ▼▼▼▼                    ▼▼▼▼
                       A   D   V   E   N   T   U   R   E
"""


SUBTITLES = [
    "A Game About Mopping in Space",
    "Now With 40% More Frakking",
    "Adama Still Doesn't Know Your Name",
    "So Say We All. So Say YOU All. Say It.",
    "Where Every NPC Forgets Your Face",
    "Featuring Six (And Six. And Six.)",
    "Like Triad But With More Crying",
    "It's Just A Vat, Specialist",
    "Toilets, Coolant, Eventually Hero",
    "Now Playing on a Battlestar Near You",
]


NAME_PROMPT = "INTERCOM: STATE YOUR NAME FOR THE DUTY ROSTER, SPECIALIST.\n> "


def show_title(io: LocalIO) -> None:
    io.send(TITLE_ART)
    io.send("              " + random.choice(SUBTITLES))
    io.send("")
    io.send("              [press enter to begin your shift]")
    try:
        io.receive("")
    except Exception:
        pass


def prompt_for_name(io: LocalIO) -> str:
    while True:
        raw = io.receive(NAME_PROMPT).strip()
        if not raw:
            io.send("INTERCOM: I CAN'T HEAR YOU OVER THE FRAKKIN' VENTS, TRY AGAIN.")
            continue
        if not is_safe_name(raw):
            io.send("INTERCOM: NAME MUST BE LETTERS, NUMBERS, OR UNDERSCORES, UP TO 32 CHARACTERS, SPECIALIST. TRY AGAIN.")
            continue
        return raw


def build_world(name: str, ng_plus_context: dict | None) -> "WorldState":
    world = new_world(name, "env_control")
    if ng_plus_context and ng_plus_context.get("ng_plus"):
        world.flags["ng_plus"] = True
        world.flags["ng_plus_count"] = ng_plus_context.get("ng_plus_count", 1)
        world.flags["previous_ending"] = ng_plus_context.get("previous_ending")
    return world


def main() -> int:
    io = LocalIO()
    show_title(io)
    name = prompt_for_name(io)
    io.send(f"\nINTERCOM: ACKNOWLEDGED, SPECIALIST {name.upper()}. WELCOME TO ANOTHER FRAKKIN' SHIFT.\n")

    ng_plus_context: dict | None = None
    while True:
        if ng_plus_context and ng_plus_context.get("ng_plus"):
            io.send("")
            io.send(
                "── ALL OF THIS HAS HAPPENED BEFORE ──\n\n"
                "You wake up. Again. The intercom is the same. The bunk is the same.\n"
                "Hadrian is the same. The dent without a story is, you swear, in a\n"
                "different place than you remembered. You shake it off. Mostly."
            )
            io.send("")
        world = build_world(name, ng_plus_context)
        session = Session(io=io, world=world)
        next_action = session.run()
        if not next_action or not next_action.get("ng_plus"):
            return 0
        ng_plus_context = next_action


if __name__ == "__main__":
    sys.exit(main())
