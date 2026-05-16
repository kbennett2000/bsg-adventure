"""Content package. Importing it triggers registration of all rooms/npcs/items."""

from . import items  # noqa: F401  — must come before rooms (rooms reference item ids)
from . import npcs   # noqa: F401
from . import rooms  # noqa: F401
