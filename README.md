# BSG Adventure

A terminal-based parser text adventure. Parody of *Battlestar Galactica* (2004
reboot) from the POV of a Specialist 3rd Class assigned to environmental systems.

You mop. You reroute coolant. You refill the XO's "water" bottle. The senior
staff have melodramatic affairs around you. They do not remember your name. You,
through a series of small competent decisions and one (1) misplaced napkin, will
probably save the fleet.

Or get spaced. Or end up in a Cylon love triangle.

So say we all.

---

## Install

Requires **Python 3.11+**. Standard library only — no pip, no venv, no
dependencies.

```bash
git clone <repo>
cd bsg-adventure
python3 main.py
```

That's it.

### Save files

Saves live in `./saves/<player_name>/` next to the game. They survive reboots.
Override the location with `BSG_SAVE_DIR`:

```bash
BSG_SAVE_DIR=/var/lib/bsg python3 main.py
```

Each save is JSON, written atomically (tmp + fsync + rename), versioned for
future format migrations.

### Multi-session over LAN

Not in this build yet. The engine has the IO abstraction in place so the
server slots in later. For now: single local terminal session.

---

## Command reference

### Core verbs

| Verb | Synonyms | What it does |
|---|---|---|
| `look` | `l` | Describe where you are (long form) |
| `examine <thing>` | `x`, `inspect`, `check`, `read` | Get a closer look |
| `go <direction>` | `move`, `walk`, also raw `n`/`s`/`e`/`w`/`up`/`down` | Move |
| `take <item>` | `get`, `grab`, `pick` | Pick something up |
| `drop <item>` | `leave`, `discard` | Put something down |
| `inventory` | `i`, `inv` | What you're carrying |
| `talk to <person>` | `speak`, `ask` | Start a conversation |
| `talk to <person> about <X>` | `ask <person> about <X>` | Get specific |
| `use <item>` | | Interact with an item |
| `use <item> on <target>` | | Use one thing on another |
| `give <item> to <person>` | `hand` | Hand something over |
| `eat <item>` | `bite` | Eat. With consequences. |
| `drink <item>` | `sip`, `chug` | Drink. With more consequences. |
| `wait` | `z` | Let a turn pass |
| `save [slot]` | | Save your game to a named slot |
| `load [slot]` | `restore` | Load it back |
| `help` | `?` | This list, briefly |
| `quit` | `exit`, `q` | Leave the ship |

### Flavor verbs

| Verb | What it does |
|---|---|
| `salute` | Render proper respect. Nobody returns it. Dignity -1. |
| `frak` | Express yourself. Burns a turn. Different lament every time. |

### Movement shortcuts

- `n` / `s` / `e` / `w` — single-letter directions
- `up` / `down` — for ladders, lifts, catwalks
- `out` — many rooms have an `out` exit that takes you back to the corridor
- Articles (`the`, `a`, `an`) and small connectors (`to`, `at`, `with`) are
  stripped — `go to the east` works the same as `e`

### Save slots

- Slot names are sanitized to `[A-Za-z0-9_]{1,32}`
- `save` with no slot saves to `default`
- `load` with no slot loads from `default`
- `auto` is reserved — written on quit and every 10 turns
- Reconnecting with the same player name auto-resumes from `auto.json`

---

## The world

Thirteen rooms across three decks of the *Galactica*:

- **Deck 5 (where you live):** Environmental Control, Corridor C-12,
  Mess Hall, The Head
- **Mid-deck:** Corridor B-7, Pilots' Rec Room, Hangar Deck,
  Baltar's Lab
- **Officer country:** Corridor A, Sickbay, Adama's Quarters, Brig,
  Observation Deck, CIC

Get to CIC. Get there with something in your pocket. Don't get spaced on
the way.

### The people

You will meet, in no particular order: Colonel Tigh (XO, drinks "water"),
Crewman Hadrian (your bunkmate, knows everyone's business), Admiral Adama
(speaks in proverbs), Lieutenant Thrace (offers triad, arm wrestling, or
making out — pick one), Captain Apollo (will mistake you for someone he has
feelings about), Doctor Baltar (already mid-conversation when you arrive — with
whom is unclear), A Number Six (your shift supervisor, probably), and
President Roslin (will ask if you're hiding a prophecy; you might be).

### The three endings

Three ways for the day to go.

- **HERO** — accidentally save the fleet by delivering a small, crumpled,
  load-bearing piece of paper to the right person at the right time.
- **SPACED** — learn too much about the XO's recreational habits and his
  command-meeting calendar. Out the airlock. Tearfully.
- **CYLON LOVE TRIANGLE** — get romantically entangled with your shift
  supervisor. And the next one. They look the same. They hate each other.
  You're fine with this.

---

## Hacking

### Architecture

Clean engine/content split. `engine/` is generic interactive-fiction
machinery — no BSG references; reusable for any parser game. `content/` is
all the BSG flavor.

### Add a room

Append a `Room(...)` to `content/rooms.py` and `register_room(...)` it.
Done. The engine discovers it via the registry.

### Add an NPC

Define an `NPC(...)` with an `on_talk(world, topic)` callback in
`content/npcs.py` and `register_npc(...)` it. Topics are matched against
keys in your dialogue dict.

### Add an item

Same pattern in `content/items.py`. Items can have `on_use`, `on_eat`,
`on_drink` callbacks. Dynamic descriptions are supported by attaching a
`_dynamic_description` function to the item (see the napkin).

### Add ambient flavor

Append a line (or a callable taking `world`) to `content/flavor.py` and
register it in `install()`. The engine rolls a die every turn and prints
one at low probability.

### Tests

Stdlib-only — no pytest required.

```bash
python3 run_tests.py            # all
python3 run_tests.py parser     # one suite by substring
```

53 tests cover: parser, save/load atomicity, the opening quest flow,
all three endings, every NPC's default dialogue, ambient events on and
off, and the first-visit / revisit room logic.

---

## Known bugs

So say we all.
