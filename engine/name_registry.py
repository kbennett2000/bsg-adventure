"""Shared player-name claim registry.

One canonical instance is shared by the TCP and HTTP listeners so a player
who is connected via telnet cannot have a second session opened via the
browser under the same name (and vice versa). This matters because the
autosave file path is keyed by player_name and concurrent writers would
race.

The registry also enforces a max-sessions cap across all transports
combined — a small LAN host shouldn't be DoS'd by one bored housemate
opening 50 browser tabs."""

import threading


class NameRegistry:
    def __init__(self, max_sessions: int) -> None:
        self._active: set[str] = set()
        self._lock = threading.Lock()
        self.max_sessions = max_sessions

    def claim(self, name: str) -> bool:
        with self._lock:
            if name in self._active:
                return False
            if len(self._active) >= self.max_sessions:
                return False
            self._active.add(name)
            return True

    def release(self, name: str) -> None:
        with self._lock:
            self._active.discard(name)

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._active

    def refusal_message(self, name: str) -> str:
        with self._lock:
            full = len(self._active) >= self.max_sessions
            already = name in self._active
        if already:
            return (
                f"\nThere's already a Specialist {name} aboard, specialist.\n"
                "The duty roster is many things, but it is not a frakkin' "
                "polygamist. Find another terminal."
            )
        if full:
            return (
                "\nThe frakkin' ship is full, specialist. Eight already aboard.\n"
                "Come back when one of them gets spaced. Statistically this won't\n"
                "be long."
            )
        return "\nConnection refused. Try again, specialist."
