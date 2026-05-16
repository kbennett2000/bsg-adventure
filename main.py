"""Entry point. Local single-player by default; `--serve` for LAN hosting."""

import argparse
import os
import random
import sys

import content  # noqa: F401  — triggers all content registration
from engine.io import Disconnected, LocalIO
from engine.save import is_safe_name
from engine.session import Session
from engine.world import new_world


# Names that would collide with the quit-verb sentinel. Reserved so a player
# can't be named "quit" (and a network disconnect at the name prompt can't
# silently create a player called "quit").
RESERVED_NAMES = {"quit", "exit", "q"}


TITLE_ART = """
                          ╔═══════════════════╗
                          ║░░░░░░░░░░░░░░░░░░░║
                          ║░░░░░░░░░░░░░░░░░░░║
                          ╚═════════╤═════════╝
                                    │
 ╔══════════════════════════════════╧═════════════════════════════════╗
 ║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║═══▶
 ║▓▓▓▓▓▓B A T T L E S T A R   G A L A C T I C A     B S G - 7 5▓▓▓▓▓▓▓║═══▶
 ║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║═══▶
 ╚══════════════════════════════════╤═════════════════════════════════╝
                                    │
                          ╔═════════╧═════════╗
                          ║░░░░░░░░░░░░░░░░░░░║
                          ║░░░░░░░░░░░░░░░░░░░║
                          ╚═══════════════════╝

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


def show_title(io) -> None:
    io.send(TITLE_ART)
    io.send("              " + random.choice(SUBTITLES))
    io.send("")
    io.send("              [press enter to begin your shift]")
    # If the receive fails (Disconnected from NetIO, KeyboardInterrupt, etc.),
    # let it propagate to the caller's handler so it can be logged/dispatched.
    io.receive("")


def prompt_for_name(io) -> str:
    """Prompt for a player name. Raises engine.io.Disconnected if the user
    (or the transport) ends the prompt: stdin EOF on LocalIO becomes the
    literal string 'quit' which we treat as intentional exit; NetIO raises
    Disconnected directly. Either way, we never accept a quit-verb token as
    a player name (that used to silently create a save called 'quit/')."""
    while True:
        raw = io.receive(NAME_PROMPT).strip()
        if not raw:
            io.send("INTERCOM: I CAN'T HEAR YOU OVER THE FRAKKIN' VENTS, TRY AGAIN.")
            continue
        if raw.lower() in RESERVED_NAMES:
            # LocalIO returns 'quit' on stdin EOF — that's an intentional exit.
            # A live player typing 'quit' at the name prompt also wants to exit.
            # Either way: don't create a player with this name.
            raise Disconnected("user exited at name prompt")
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


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="bsg-adventure",
        description="Battlestar Galactica Adventure. Single-player by default; --serve to host on LAN.",
    )
    p.add_argument(
        "--serve",
        action="store_true",
        help="Run as a LAN multi-session server instead of local single-player.",
    )
    p.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("BSG_PORT", "4404")),
        help="TCP port to listen on (server mode). Default 4404. Env: BSG_PORT.",
    )
    p.add_argument(
        "--bind",
        default=os.environ.get("BSG_BIND_ADDR", "0.0.0.0"),
        help="Address to bind to (server mode). Default 0.0.0.0. Env: BSG_BIND_ADDR.",
    )
    p.add_argument(
        "--max-sessions",
        type=int,
        default=int(os.environ.get("BSG_MAX_SESSIONS", "8")),
        help="Max concurrent connections (server mode). Default 8. Env: BSG_MAX_SESSIONS.",
    )
    p.add_argument(
        "--idle-timeout",
        type=int,
        default=int(os.environ.get("BSG_IDLE_TIMEOUT", "1800")),
        help="Per-connection idle timeout in seconds (server mode). Default 1800. Env: BSG_IDLE_TIMEOUT.",
    )
    return p.parse_args(argv)


def run_local() -> int:
    io = LocalIO()
    try:
        show_title(io)
        name = prompt_for_name(io)
    except Disconnected:
        return 0
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


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.serve:
        from engine.server import serve_forever
        serve_forever(
            bind_addr=args.bind,
            port=args.port,
            max_sessions=args.max_sessions,
            idle_timeout=args.idle_timeout,
        )
        return 0
    return run_local()


if __name__ == "__main__":
    sys.exit(main())
