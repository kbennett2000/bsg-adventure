"""Per-session game loop. Owns world + io + lifecycle for one player."""

from dataclasses import dataclass

from . import commands, parser, save as save_module
from .io import IO
from .world import WorldState, new_world


AUTOSAVE_EVERY_N_TURNS = 10


@dataclass
class Session:
    io: IO
    world: WorldState

    def run(self) -> None:
        # Opening room description fires on first entry via on_enter hook
        room_text = commands.describe_room(self.world)
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
                if self.world.turn % AUTOSAVE_EVERY_N_TURNS == 0:
                    self._autosave_quiet()
            if result.quit:
                self._autosave_quiet()
                break

    def _autosave_quiet(self) -> None:
        try:
            save_module.save_world(self.world, slot="auto")
        except Exception:
            # Don't crash gameplay on autosave failure. Could log here.
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
