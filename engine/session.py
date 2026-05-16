"""Per-session game loop. Owns world + io + lifecycle for one player."""

from dataclasses import dataclass

from . import commands, events, parser, save as save_module
from .io import IO
from .world import WorldState, bump_stat, get_stat, new_world


AUTOSAVE_EVERY_N_TURNS = 10
EXHAUSTION_PER_TICK = 1            # +1 stat per tick
EXHAUSTION_TICK_EVERY = 1          # every N turns
COLLAPSE_LOSES_ITEMS = ("canteen", "mop", "algae_bar")  # napkin is spared


@dataclass
class Session:
    io: IO
    world: WorldState

    def run(self) -> None:
        if self.world.current_room not in self.world.visited_rooms:
            self.world.visited_rooms.append(self.world.current_room)
        room_text = commands.describe_room(self.world, first_visit=True)
        self.io.send(room_text)
        from .registry import ROOMS
        room = ROOMS[self.world.current_room]
        if room.on_enter:
            extra = room.on_enter(self.world)
            if extra:
                self.io.send("")
                self.io.send(extra)

        while True:
            self.io.send("")
            raw = self.io.receive()
            if raw is None:
                break
            cmd = parser.parse(raw)
            result = commands.dispatch(self.world, cmd, self)
            if result.text:
                self.io.send(result.text)
            if result.advance_turn:
                self.world.turn += 1
                self._tick_exhaustion()
                # Post-tick threshold checks
                if self._check_collapse():
                    pass  # _check_collapse handles its own messaging
                if self._check_suspicion_spaced():
                    self._autosave_quiet()
                    self.io.send("")
                    self.io.send("── END ──")
                    break
                ambient = events.tick(self.world)
                if ambient:
                    self.io.send("")
                    self.io.send(ambient)
                if self.world.turn % AUTOSAVE_EVERY_N_TURNS == 0:
                    self._autosave_quiet()
            if result.ended:
                self._autosave_quiet()
                self.io.send("")
                self.io.send("── END ──")
                break
            if result.quit:
                self._autosave_quiet()
                break

    def _tick_exhaustion(self) -> None:
        if self.world.turn % EXHAUSTION_TICK_EVERY == 0:
            bump_stat(self.world, "exhaustion", EXHAUSTION_PER_TICK)

    def _check_collapse(self) -> bool:
        """At exhaustion 100, the player collapses and wakes up in sickbay
        missing items. Returns True if collapse fired."""
        if get_stat(self.world, "exhaustion") < 100:
            return False
        self.io.send("")
        self.io.send(
            "Your knees buckle.\n\n"
            "The deck plate rises to meet you with the specific patience of a deck "
            "plate that has met a lot of specialists this way. You hear someone — "
            "probably Hadrian — say 'oh frak not AGAIN' from somewhere far away. "
            "Then there is a quality of silence you have only previously associated "
            "with sleep, vacuum, and that one time in basic."
        )
        # Lose items (except napkin — the player's grip is divine)
        lost = []
        for item_id in list(self.world.inventory):
            if item_id in COLLAPSE_LOSES_ITEMS:
                self.world.inventory.remove(item_id)
                lost.append(item_id)
        # Move to sickbay
        self.world.current_room = "sickbay"
        if "sickbay" not in self.world.visited_rooms:
            self.world.visited_rooms.append("sickbay")
        # Reset exhaustion to a tired-but-functional baseline
        from .world import set_stat
        set_stat(self.world, "exhaustion", 30)
        # Re-render sickbay
        self.io.send("")
        self.io.send(
            "You wake up. Sickbay. Doc Cottle is somewhere. Smoking. You can smell "
            "him from here. Someone has put a blanket over you. The blanket has "
            "your name on it, written in marker, by someone who knows you somehow."
        )
        if lost:
            from .registry import ITEMS
            names = ", ".join(ITEMS[i].name for i in lost)
            self.io.send("")
            self.io.send(f"You are missing: {names}. You don't know where they went. You have suspicions.")
        self.io.send("")
        self.io.send(commands.describe_room(self.world, first_visit=False))
        return True

    def _check_suspicion_spaced(self) -> bool:
        """At suspicion 100, anywhere, the player is intercepted and spaced.
        Returns True if the ending fired."""
        if get_stat(self.world, "suspicion") < 100:
            return False
        if self.world.flags.get("__ended__"):
            return False
        self.world.flags["__ended__"] = "spaced"
        self.io.send("")
        self.io.send(
            "Two MPs you have never seen before turn the corner. They are calm. They\n"
            "are professional. They do not, when they take your arms, look at your\n"
            "face.\n\n"
            "'Specialist. Come with us, please.'\n\n"
            "Behind them, you catch a glimpse of Colonel Tigh. He is not looking at\n"
            "you. He is looking at a fire extinguisher, which is — you note, on the\n"
            "way past — newly dented at face height.\n\n"
            "The airlock is short. The ceremony is shorter.\n\n"
            "── ENDING: SPACED FOR KNOWING TOO MUCH ──"
        )
        return True

    def _autosave_quiet(self) -> None:
        try:
            save_module.save_world(self.world, slot="auto")
        except Exception:
            pass


def start_session_local(io: IO, player_name: str, starting_room: str) -> Session:
    """Start a fresh local session (or resume autosave if one exists for this name)."""
    if save_module.has_save(player_name, "auto"):
        try:
            world = save_module.load_world(player_name, "auto")
            io.send(f"(Resumed autosave for {player_name}, turn {world.turn}.)")
        except Exception:
            world = new_world(player_name, starting_room)
    else:
        world = new_world(player_name, starting_room)
    return Session(io=io, world=world)
