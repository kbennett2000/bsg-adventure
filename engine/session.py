"""Per-session game loop. Owns world + io + lifecycle for one player."""

from dataclasses import dataclass, field
from typing import Callable, Optional

from . import commands, events, parser, save as save_module
from .io import IO, Disconnected
from .world import WorldState, bump_stat, get_stat, new_world, shift_name, tick_shift_counter


AUTOSAVE_EVERY_N_TURNS = 10
EXHAUSTION_PER_TICK = 1            # +1 stat per tick
EXHAUSTION_TICK_EVERY = 1          # every N turns
COLLAPSE_LOSES_ITEMS = ("canteen", "mop", "algae_bar")  # napkin is spared

# Hidden Cylon mechanic. cylon_vibes ≥ this threshold silently flips a hidden
# flag; from that point on, the player resurrects on "death" endings (spaced,
# forbidden_knowledge) instead of game-over. Three resurrections fire the
# unique Download Complete ending. None of this is surfaced to the player.
CYLON_THRESHOLD = 75
DEATH_ENDINGS = ("spaced", "forbidden_knowledge")
RESURRECTION_DOWNLOAD_AT = 3       # third resurrection becomes Download Complete


# Sentinel returned by ending-handling helpers when the player resurrected
# and the session loop should continue (rather than returning a NG+ dict).
_CONTINUE = object()


def _noop_log(_msg: str) -> None:
    """Default log function — silent. Server mode injects its own."""


@dataclass
class Session:
    io: IO
    world: WorldState
    # Optional log sink for failure modes that shouldn't crash gameplay but
    # also shouldn't be invisible (e.g., epitaph render failure during ending
    # finalize). Server mode wires this to its log_fn so journald sees it.
    log_fn: Callable[[str], None] = field(default=_noop_log)

    def run(self) -> Optional[dict]:
        """Run the per-session game loop.

        Returns None on normal quit, or a dict describing a new-game-plus
        request that main() should honor by spinning up a fresh session."""
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
            try:
                raw = self.io.receive()
            except Disconnected:
                # Network player dropped. Save and exit cleanly.
                self._autosave_quiet()
                return None
            if raw is None:
                break
            # The Quorum Press Conference is a self-contained sub-mode. While
            # it's active, ALL input is routed to its handler — the player has
            # no normal verbs until the conference ends (or they quit).
            if self.world.flags.get("press_active"):
                from content import press
                result = press.handle_input(self.world, raw)
                if result.text:
                    self.io.send(result.text)
                if result.quit:
                    self._autosave_quiet()
                    return None
                continue
            cmd = parser.parse(raw)
            result = commands.dispatch(self.world, cmd, self)
            if result.text:
                self.io.send(result.text)
            if result.advance_turn:
                self.world.turn += 1
                self._tick_exhaustion()
                self._check_collapse()
                # Silent Cylon flag flip — checked after every advancing turn
                # so any path that pushes cylon_vibes over the threshold is caught.
                self._check_cylon_threshold()
                # Watch-clock tick. May advance a shift; trigger any
                # cross-shift consequences (duty roster, hunger, day rollover).
                if tick_shift_counter(self.world):
                    self._on_shift_change()
                if self._check_suspicion_spaced():
                    nxt = self._handle_end_or_resurrect()
                    if nxt is _CONTINUE:
                        continue
                    return nxt
                ambient = events.tick(self.world)
                if ambient:
                    self.io.send("")
                    self.io.send(ambient)
                if self.world.turn % AUTOSAVE_EVERY_N_TURNS == 0:
                    self._autosave_quiet()
            if result.ended:
                nxt = self._handle_end_or_resurrect()
                if nxt is _CONTINUE:
                    continue
                return nxt
            if result.quit:
                self._autosave_quiet()
                return None

        return None

    def _finalize_ending(self) -> None:
        """Print the epitaph, unlock any achievements, autosave, then the END marker.

        Both the epitaph render and the achievement check are wrapped in
        try/except so a single failure doesn't crash the player out of an
        ending. Failures are routed to `log_fn` so the server operator can
        see them in journald — they used to be totally silent."""
        ending_id = self.world.flags.get("__ended__")
        # Epitaph (tragicomic closer) keyed off the ending id.
        try:
            from content.epitaphs import pick_epitaph
            ep = pick_epitaph(ending_id)
            if ep:
                self.io.send("")
                self.io.send(ep)
        except Exception as exc:
            self.log_fn(f"[finalize-epitaph-error] ending={ending_id!r} {exc!r}")
        # Achievement check + display (persisted to disk).
        try:
            from content.achievements import check_and_unlock, render_unlock_banner
            unlocked = check_and_unlock(self.world)
            for ach in unlocked:
                self.io.send("")
                self.io.send(render_unlock_banner(ach))
        except Exception as exc:
            self.log_fn(f"[finalize-achievement-error] player={self.world.player_name!r} {exc!r}")
        self._autosave_quiet()
        self.io.send("")
        self.io.send("── END ──")

    def _prompt_new_game_plus(self) -> Optional[dict]:
        """Ask if the player wants to begin again with one carried-over flag.

        Returns a dict for main() to honor, or None for normal exit."""
        self.io.send("")
        self.io.send(
            "Begin again, specialist? Your shift, somehow, has not ended.\n"
            "Some things you will remember. Most you will not. [y/n]"
        )
        try:
            raw = self.io.receive("> ").strip().lower()
        except Exception:
            return None
        if raw not in ("y", "yes"):
            return None
        return {
            "ng_plus": True,
            "previous_ending": self.world.flags.get("__ended__"),
            "ng_plus_count": self.world.flags.get("ng_plus_count", 0) + 1,
        }

    def _tick_exhaustion(self) -> None:
        if self.world.turn % EXHAUSTION_TICK_EVERY == 0:
            bump_stat(self.world, "exhaustion", EXHAUSTION_PER_TICK)

    def _on_shift_change(self) -> None:
        """Banner + cross-shift consequences (duty rollover, hunger penalty).
        Called whenever the watch clock advances a shift, whether via the
        auto-tick or via the `sleep` verb."""
        self.io.send("")
        self.io.send(f"── {shift_name(self.world).upper()}  (Day {self.world.day}) ──")
        # Content-side cross-shift hooks (duty / hunger / etc.). Imported lazily
        # to avoid engine→content circularity.
        try:
            from content.duties import on_shift_change
            extra = on_shift_change(self.world)
            if extra:
                self.io.send("")
                self.io.send(extra)
        except Exception as exc:
            self.log_fn(f"[on-shift-change-error] {exc!r}")

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

    # ─── Hidden Cylon mechanic ─────────────────────────────────────────────

    def _check_cylon_threshold(self) -> None:
        """Silently set the hidden is_cylon flag when cylon_vibes crosses
        the threshold. Never surfaced to the player; the world reacts via
        other hooks (Cottle bloodwork remark, detector behavior, ambient
        Watchtower frequency, certain examines)."""
        if self.world.flags.get("is_cylon"):
            return
        if get_stat(self.world, "cylon_vibes") >= CYLON_THRESHOLD:
            self.world.flags["is_cylon"] = True

    def _handle_end_or_resurrect(self):
        """Common path for any ending the loop just triggered. If the player
        is a Cylon and this is a 'death' ending, intercept it with
        resurrection (return _CONTINUE so the caller continues the loop).
        Otherwise finalize and prompt for new-game-plus."""
        if self._maybe_resurrect():
            return _CONTINUE
        self._finalize_ending()
        return self._prompt_new_game_plus()

    def _maybe_resurrect(self) -> bool:
        """If the player is a Cylon and the current ending is a 'death'
        ending (spaced or forbidden_knowledge), perform resurrection.
        Returns True if resurrection happened; False otherwise."""
        if not self.world.flags.get("is_cylon"):
            return False
        ending_id = self.world.flags.get("__ended__")
        if ending_id not in DEATH_ENDINGS:
            return False
        new_count = self.world.flags.get("resurrection_count", 0) + 1
        self.world.flags["resurrection_count"] = new_count
        if new_count >= RESURRECTION_DOWNLOAD_AT:
            # Third resurrection → Download Complete ending replaces normal
            # resurrection. The original death ending text already printed;
            # we override __ended__ and append the Download Complete monologue,
            # then let _finalize_ending handle the epitaph + END banner.
            self.world.flags["__ended__"] = "download_complete"
            from content.cylon import DOWNLOAD_COMPLETE_TEXT
            self.io.send("")
            self.io.send(DOWNLOAD_COMPLETE_TEXT)
            return False    # finalize handles the new ending normally
        # Normal resurrection: clear the death ending, apply world drift,
        # print the resurrection narrative, and continue the loop.
        self.world.flags.pop("__ended__", None)
        self._apply_resurrection_drift(new_count)
        from content.cylon import resurrection_text
        self.io.send("")
        self.io.send(resurrection_text(new_count))
        return True

    def _apply_resurrection_drift(self, resurrection_number: int) -> None:
        """Each resurrection makes the world slightly more wrong. Mutates the
        WorldState in place. The shape of the drift escalates with the count."""
        from .world import set_stat
        w = self.world
        # Time advances: the fleet has jumped one step further.
        w.day += 1
        w.shift = 0
        w.turns_this_shift = 0
        # Body reset.
        set_stat(w, "exhaustion", 0)
        set_stat(w, "morale", max(20, get_stat(w, "morale") // 2))
        set_stat(w, "suspicion", get_stat(w, "suspicion") // 2)
        # cylon_vibes stays — you are, increasingly, what you are.
        # Player wakes in their bunk (resurrection tank → env_control).
        w.current_room = "env_control"
        # Per-resurrection NPC drift.
        if resurrection_number == 1:
            w.flags["npc_suspicious_hadrian"] = True
        elif resurrection_number == 2:
            w.flags["npc_dead_helo"] = True
        # Day-roll flags reset so duty/hunger don't double-trigger:
        for k in (
            "duty_today", "duty_mopped_today", "duty_console_today",
            "duty_brig_today", "duty_baltar_today", "ate_today",
        ):
            w.flags.pop(k, None)
        w.flags["_last_rollover_day"] = w.day


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
