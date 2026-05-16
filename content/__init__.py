"""Content package. Importing it triggers registration of all rooms/npcs/items."""

from . import items      # noqa: F401  — must come before rooms (rooms reference item ids)
from . import npcs       # noqa: F401
from . import rooms      # noqa: F401
from . import flavor     # noqa: F401
from . import schedules  # noqa: F401  — NPC schedules; engine reads at runtime
from . import duties     # noqa: F401  — duty roster; engine calls on_shift_change

flavor.install()
