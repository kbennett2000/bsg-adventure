"""Entry point for local play."""

import sys

import content  # noqa: F401  — triggers all content registration
from engine.io import LocalIO
from engine.save import is_safe_name
from engine.session import start_session_local


OPENING = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║              B A T T L E S T A R   G A L A C T I C A                 ║
║                                                                      ║
║                      ── DECK FIVE  ──                                ║
║                                                                      ║
║   You are a Specialist Third Class. You clean toilets and            ║
║   reroute coolant lines. Today, like every day, will be              ║
║   frakking long.                                                     ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

NAME_PROMPT = "INTERCOM: STATE YOUR NAME FOR THE DUTY ROSTER, SPECIALIST.\n> "


def prompt_for_name(io) -> str:
    while True:
        raw = io.receive(NAME_PROMPT).strip()
        if not raw:
            io.send("INTERCOM: I CAN'T HEAR YOU OVER THE FRAKKIN' VENTS, TRY AGAIN.")
            continue
        if not is_safe_name(raw):
            io.send("INTERCOM: NAME MUST BE LETTERS, NUMBERS, OR UNDERSCORES, UP TO 32 CHARACTERS, SPECIALIST. TRY AGAIN.")
            continue
        return raw


def main() -> int:
    io = LocalIO()
    io.send(OPENING)
    name = prompt_for_name(io)
    io.send(f"\nINTERCOM: ACKNOWLEDGED, SPECIALIST {name.upper()}. WELCOME TO ANOTHER FRAKKIN' SHIFT.\n")
    session = start_session_local(io, player_name=name, starting_room="env_control")
    session.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
