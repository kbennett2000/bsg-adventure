# BSG Adventure

```
        ╔═════════════╗
        ║░░░░░░░░░░░░░║
        ╚══════╤══════╝
 ╔═════════════╧══════════════╗
 ║▓▓▓ B S G - 7 5  GALACTICA ▓║═══▶
 ╚═════════════╤══════════════╝
        ╔══════╧══════╗
        ║░░░░░░░░░░░░░║
        ╚═════════════╝
```

A terminal-based parser text adventure. Parody of Battlestar Galactica (2004 reboot)
from the POV of a Specialist 3rd Class assigned to environmental systems. The player
mops, reroutes coolant, and refills the XO's "water" bottle while the senior staff have
melodramatic affairs around them.

**Single-player per session, multi-session over LAN.** The game itself is single-player
— one player, one Galactica, one specialist. But the host machine runs a server, and
anyone on the same home network can connect from their own terminal and play their own
independent session. Sessions do not share a world; two players connecting at the same
time are each playing their own copy. No internet exposure — LAN only.

The comedy is contrast: menial labor in the foreground, operatic space drama in the
background. The player is invisible to the officers — even after meaningful encounters,
they will not remember the player's name.

---

## Architecture

Clean separation between **engine** (generic interactive fiction machinery) and
**content** (this specific game's rooms, NPCs, items, dialogue). The engine should
never import from content; content registers itself with the engine.

### Directory layout

```
bsg-adventure/
├── CLAUDE.md                  # this file
├── README.md                  # player-facing (to be written later)
├── main.py                    # entry point; modes: --serve (default), --local (dev)
├── engine/
│   ├── __init__.py
│   ├── parser.py              # tokenize + match input → (verb, direct_obj, indirect_obj)
│   ├── world.py               # WorldState: current room, inventory, flags, turn count
│   ├── commands.py            # verb handlers (go, look, take, …); dispatch table
│   ├── loop.py                # per-session game loop; prompt → parse → dispatch → render
│   ├── io.py                  # IO abstraction; LocalIO + NetIO (TCP) + WebIO (browser) + ScriptedIO (tests)
│   ├── server.py              # ThreadingTCPServer for telnet/nc clients
│   ├── webserver.py           # ThreadingHTTPServer + SSE/POST routes for the browser client
│   ├── name_registry.py       # shared player-name claim across TCP + HTTP listeners
│   ├── session.py             # per-connection: identity, WorldState, IO, lifecycle
│   ├── save.py                # serialize/deserialize WorldState to JSON; atomic writes
│   ├── events.py              # turn-based event hooks (e.g., Tigh wanders by on T+5)
│   └── registry.py            # content registers rooms/npcs/items/verbs here
├── web/                       # browser client (served by engine/webserver.py)
│   ├── index.html             # single-page terminal UI; references only /style.css /app.js
│   ├── style.css              # green-on-black CRT theme; no external fonts or imports
│   └── app.js                 # vanilla JS: EventSource for output, fetch POST for input
├── content/
│   ├── __init__.py            # bulk-imports the modules below so registration fires
│   ├── rooms.py               # all 13 room definitions
│   ├── npcs.py                # NPC definitions + per-NPC dialogue state machines
│   ├── items.py               # item definitions + use-handlers
│   ├── dialogue.py            # talk topics and response trees, keyed by (npc, topic)
│   ├── quest.py               # main-quest flag transitions, ending triggers
│   └── flavor.py              # ambient text: officer melodrama overheard each turn
├── saves/                     # JSON save files; one subdir per player (gitignored)
│   └── <player_name>/
│       ├── auto.json          # autosave (overwritten on disconnect + every N turns)
│       └── <slot>.json        # named saves via `save <slot>`
└── tests/
    ├── test_parser.py
    ├── test_world.py
    ├── test_save.py
    └── test_server.py          # accept loop, two concurrent sessions don't interfere
```

### Data model

Content lives as plain Python data structures (dicts and dataclasses), not classes
with behavior. Behavior (use-handlers, talk-handlers, event triggers) is registered
as plain functions keyed by id. This keeps content authoring approachable and
hot-reloadable later if we want.

- **Room**: `id`, `name`, `short_desc`, `long_desc`, `exits: dict[direction → room_id]`,
  `items: list[item_id]`, `npcs: list[npc_id]`, `on_enter: callable | None`,
  `ambient: list[str]` (random flavor lines printed on look or per turn).
- **NPC**: `id`, `name`, `aliases: list[str]` (e.g. `["tigh", "colonel", "xo"]`),
  `mood: str`, `topics: dict[str → str | callable]`, `remembers_player: bool = False`
  (almost always False — see Tone Bible).
- **Item**: `id`, `name`, `aliases`, `desc`, `takeable: bool`, `use: callable | None`,
  `use_on: dict[target_id → callable] | None`.
- **WorldState**: `player_name`, `current_room`, `inventory: list[item_id]`,
  `flags: dict[str, Any]`, `turn: int`, `npc_state: dict[npc_id, dict]`,
  `item_state: dict[item_id, dict]`.
- **Session** (engine, not content): `player_name`, `io: IO`, `world: WorldState`,
  `connected_at`, `last_activity_at`. Owned by the server, one per connection.

### Save files

JSON, written to `saves/<player_name>/<slot>.json`. We serialize **WorldState only** —
never the content definitions, which always come from code at load time. A save is
essentially a snapshot of mutable state plus a content version string for
compatibility.

```json
{
  "version": "0.1",
  "player_name": "kara",
  "turn": 47,
  "current_room": "head_deck_5",
  "inventory": ["mop", "tighs_flask"],
  "flags": {"saw_baltar_talking_to_nobody": true, "tigh_drunk_level": 3},
  "npc_state": {"starbuck": {"mood": "punch_bulkhead", "last_seen_turn": 42}},
  "item_state": {}
}
```

**Durability — must survive host reboot.**

- `saves/` lives at a stable absolute path (configured via `BSG_SAVE_DIR` env var,
  defaulting to `<install-dir>/saves`). Never `/tmp`, never CWD-relative inside
  the running process.
- Writes are **atomic**: write to `<slot>.json.tmp`, `fsync`, `os.replace` onto
  `<slot>.json`. This prevents a half-written file if the host loses power mid-save.
- **Autosave** to `auto.json` on every clean disconnect AND every N turns (default
  N=10) so an abrupt disconnect, crash, or power loss costs at most N turns of
  progress.
- When a player reconnects with the same `player_name`, the server offers to resume
  from `auto.json` or load a named slot.
- `player_name` is sanitized to `[A-Za-z0-9_]{1,32}` before being used as a path
  segment. Anything else is rejected at connect time. No path traversal.

### Adding content

To add a room, append a dict to `content/rooms.py` and register it. No engine changes.
To add an item with a custom use behavior, define the item dict and a `use_<id>(world)`
function in `content/items.py`. Same for NPC topics. The engine discovers everything
through `engine/registry.py`.

---

## Networking and multi-session hosting

The game runs as a long-lived server process on one machine on the home LAN. Anyone
on the LAN connects from their own terminal to play. Sessions are independent — two
people connected at the same time are each playing their own copy of the story.

### Transport

Two listeners run side-by-side in the same `--serve` process. Both are
thread-per-connection (`socketserver.ThreadingTCPServer` and
`http.server.ThreadingHTTPServer`); they share one `NameRegistry` so name
claims are unique across transports. The original spec called for
asyncio; we landed on threading because the workload is purely IO-bound,
the implementation is much shorter, and the engine code stays synchronous.

- **TCP listener** — line-oriented text protocol on `0.0.0.0:4404`
  (configurable via `BSG_BIND_ADDR` / `BSG_PORT` or `--bind` / `--port`).
  Clients: `nc <host> 4404`, `telnet`, anything that speaks raw TCP.
- **HTTP listener** — single-page browser client on `0.0.0.0:4405`
  (configurable via `BSG_WEB_BIND_ADDR` / `BSG_WEB_PORT` or `--web-bind` /
  `--web-port`). The browser opens an `EventSource` against `/events?
  session=<id>` for server→browser push and POSTs lines to `/input?
  session=<id>`. Static assets (HTML/CSS/JS) live in `web/` and are
  served from the local filesystem — no CDN, no external fonts.
- Either listener can be disabled with `--no-tcp` / `--no-web`.
- **LAN only.** Both listeners share the same security stance: no auth,
  no TLS. Bind to a LAN interface, do not port-forward.

### Sessions

- Each accepted connection spawns one `Session` running its own copy of the
  per-session game loop (`engine/loop.py`). Sessions are isolated; there is no
  shared world state between them.
- On connect, the server prompts: *"Frak. Who's asking? (name):"*. The name is
  sanitized to `[A-Za-z0-9_]{1,32}`. If a save exists for that name, the server
  offers to resume.
- **Idle timeout**: 30 minutes of no input → autosave + disconnect.
- **Max concurrent sessions**: configurable cap (default 8) to keep a small LAN
  host from being overwhelmed. Excess connections get a polite refusal in
  character.
- Same `player_name` connecting twice while a session is already live → the new
  connection gets "You're already aboard, specialist." and is refused. (We do not
  attempt session migration — that's complexity for no benefit on a home LAN.)

### IO abstraction

Engine code MUST NOT call `print()` or `input()` directly. All IO goes through an
`IO` interface (`engine/io.py`) with `send(text)` and `receive(prompt) -> str`.
There are four implementations:

- **LocalIO** — wraps stdin/stdout. Used by `main.py` (no `--serve`) for solo play.
- **NetIO** — wraps a socketserver `rfile`/`wfile` pair for the TCP listener.
- **WebIO** — queue-backed; output goes onto a Queue that the SSE writer
  thread drains; input comes from a Queue that the POST `/input` handler
  pushes onto. Raises `Disconnected` when the session is closed.
- **ScriptedIO** — feeds canned input and records output. Used by tests.

This is the seam that keeps the parser/loop/commands network-agnostic. Adding a
new transport means writing one IO subclass; the engine doesn't change.

### Concurrency model

- One OS thread per session, regardless of transport. TCP gets a thread per
  accepted connection from `ThreadingTCPServer`; the browser path spawns a
  game thread at `/spawn` time and a separate SSE-writer thread per
  `/events` request.
- There is **no shared mutable state across sessions**. Each session owns its
  own WorldState. The content definitions (rooms, npcs, items) are read-only and
  shared safely between threads (set up at import time, never mutated).
- The shared `NameRegistry` enforces one-session-per-name and the global
  max-sessions cap across both transports.

### Operational notes

- The host should run the server under a process supervisor (systemd unit,
  `screen`/`tmux`, or just `python main.py --serve` in a stable working directory)
  so that it auto-restarts after a reboot.
- `saves/` must be in the same stable directory across reboots — see the Save
  files section for `BSG_SAVE_DIR`.
- A `systemd/bsg-adventure.service` example unit should ship in the repo when we
  get to operationalization. Not yet.

---

## TONE BIBLE

**All content must obey this. If a line of dialogue or description does not feel like
it belongs in this universe, rewrite it until it does.**

### Universal rules

- **"Frak" is the universal expletive.** Every character uses it. Specialists use it
  more than officers — it is class-coded. A specialist says "frak" three times per
  sentence; an officer uses it for emphasis.
- **Officers do not remember the player.** Even after meaningful, vulnerable,
  plot-relevant encounters, the next interaction starts from zero. They will ask the
  player's name and forget it inside the same scene. Never break this. The player's
  invisibility is the engine of the comedy.
- **The player is a Specialist 3rd Class in environmental systems.** Their job is
  toilets, coolant, vents, and refilling officers' "water." They are competent at
  this and proud of it. They are not a hero. They become one only by accident.

### Character voices

- **Colonel Tigh** — Jim Lahey from Trailer Park Boys, but in space. Perpetually
  buzzed. Gravelly. Speaks in nautical-shitstorm metaphors that almost cohere but
  don't ("Son, the frakkin' tide of command is comin' in, and your boots are made
  of regulation. Mop faster.") Carries a flask he calls his "water bottle." He and
  Adama have an unspoken bond that everyone except them suspects is romantic. He
  will sometimes get misty-eyed talking about Bill and not know why.

- **Adama** — speaks exclusively in cryptic gravelly proverbs that sound profound
  and mean nothing on inspection. ("A ship is only as strong as the men who hate
  each other on it." "Frak is a verb, son. So is duty.") He delivers them slowly,
  with weight, and walks away before anyone can ask follow-up questions.

- **Starbuck** — three modes only: **fight**, **frak**, **punch a bulkhead**.
  She rotates. Track which mode she's in via `npc_state["starbuck"]["mood"]` and
  cycle it on encounter. She will hit on the player in frak-mode and not recognize
  them ten minutes later in fight-mode.

- **Baltar** — carries on full animated conversations with someone who is not there.
  The player can see him doing it. If the player asks about it, he becomes
  defensive and accuses the player of being the crazy one. ("What? No. There is no
  one. I was — I was working through a problem. Out loud. Like a normal person.
  Why are you looking at me like that. Stop looking at me like that.")

- **Apollo** — himbo trapped in a love triangle he does not understand. Earnest.
  Square-jawed. Will explain his feelings to the player at length, ask the player
  for romantic advice, and then forget the conversation. Refers to all problems as
  "complicated" with a faraway look.

- **Cylons** — hot, dangerous, and possibly your shift supervisor. Treat any
  unusually attractive NPC as suspect. Cylon reveals should be played both for
  horror and for thirst.

### Specialist voice (the player's peers)

NPCs who are also specialists/deckhands speak with weariness, profanity, and a
strong class-conscious resentment of officer drama. They are the only characters
who consistently remember the player's name. They are also the only ones who say
useful things.

### Ambient melodrama

Every few turns, regardless of room, an ambient line should fire describing
officers having a meaningful moment two meters from the player while the player
is doing maintenance. Examples:

- "Apollo and Starbuck are screaming at each other about feelings near the
  starboard coolant vent. You squeeze past them with your mop."
- "Colonel Tigh stares into the middle distance, sipping his water bottle. The
  water bottle clinks like ice."
- "Baltar is having a heated argument with the bulkhead. The bulkhead is winning."

These are content in `content/flavor.py`, fired by `engine/events.py`.

---

## World structure

### Rooms (13 total — close enough to "roughly 12")

| id | name | notes |
|---|---|---|
| `cic` | Combat Information Center | Where Adama and Tigh stare meaningfully. Player isn't supposed to be here. |
| `hangar_deck` | Hangar Deck | Vipers, grease, Chief Tyrol yelling. Starbuck shows up in one of her three modes. |
| `pilots_rec` | Pilots' Rec Room | Triad table. Apollo asks the player for relationship advice. |
| `sickbay` | Sickbay | Doc Cottle smokes despite the oxygen. Cylon-detection subplot lives here. |
| `head_deck_5` | The Head (Deck 5) | The player's domain. Plot exposition gets overheard from stalls. |
| `mess_hall` | Mess Hall | Specialists eat here. Best source of intel from peers. |
| `adamas_quarters` | Adama's Quarters | Model ship on the desk. Tigh is usually already inside. |
| `brig` | Brig | Possible final destination. A Cylon is being held here. Or is she? |
| `observation_deck` | Observation Deck | Where officers go to brood. Apollo broods here on a timer. |
| `env_control` | Environmental Control | The player's actual workplace. Coolant lines, vent schematics. |
| `corridor_a` | Corridor A (Deck 5) | Junction. Baltar passes through talking to no one. |
| `corridor_b` | Corridor B (Deck 12) | Junction near hangar. Cylon shift supervisor encountered here. |
| `baltars_lab` | Baltar's Lab | Locked normally; gained later in quest. Full of "evidence" that doesn't exist. |

### Main quest spine

The player does not know they are on a quest. Each act is gated by routine work tasks.

1. **Act 1 — The Coolant Anomaly.** The player is sent to fix a vent in `env_control`.
   They discover a coolant line has been rerouted by someone who isn't on shift. The
   schematic doesn't match the ship. *Flag: `noticed_anomaly`.*

2. **Act 2 — Three things happen by accident.**
   - The player overhears, from a toilet stall in `head_deck_5`, Tigh confessing
     something to Adama about the flask. *Flag: `knows_about_flask`.*
   - The player is hit on by their attractive shift supervisor in `corridor_b`.
     The supervisor is a Cylon. *Flag: `supervisor_is_cylon`.*
   - The player is pulled into the Apollo/Starbuck/Cylon love triangle by being
     asked for advice by all three in sequence, each forgetting the player
     immediately after. *Flag: `triangle_count` increments.*

3. **Act 3 — The Choice.** The player's accumulated flags determine which ending
   path is available. The player thinks they are still just doing their job.

### Endings

- **Ending A — Accidentally Save the Fleet.** Triggered if the player has
  `noticed_anomaly` AND fixes the coolant line back to spec before turn N. They
  unknowingly prevent a Cylon sabotage. Adama gives them a medal and forgets their
  name during the ceremony.
- **Ending B — Spaced for Knowing Too Much.** Triggered if the player has
  `knows_about_flask` AND ever tells anyone (any `talk tigh about flask`,
  `talk adama about flask`, or similar). Tigh tearfully orders them out an airlock,
  apologizing the whole time.
- **Ending C — Cylon Love Triangle.** Triggered if `supervisor_is_cylon` AND
  `triangle_count >= 2` AND the player has `flirted` with the supervisor. The
  player ends up in a four-way romantic entanglement they do not understand,
  somewhere on a basestar. Apollo is also there. He is confused.

---

## Parser verbs

### Core
`go <direction>` (also `n`, `s`, `e`, `w`, `up`, `down`, `north`…), `look`,
`examine <thing>` (also `x`, `inspect`), `take <item>` (also `get`, `grab`),
`drop <item>`, `use <item>` / `use <item> on <target>`, `give <item> to <npc>`,
`talk to <npc>` / `talk to <npc> about <topic>`, `inventory` (also `i`, `inv`),
`wait` (also `z`), `save [slot]`, `load [slot]`, `help`, `quit`.

### Flavor verbs
- **`salute`** — salute the nearest officer. They do not return the salute. They
  do not see you. Free turn. May increment a hidden `dignity_lost` counter.
- **`frak`** — existential interjection. Prints a context-aware reaction.
  **Free turn** (does not advance world clock or fire ambient events). Use
  liberally. Specialists who overhear may sympathize.
- **`drink`** — has consequences. If `tighs_flask` is in inventory, drinking from
  it increments `player_drunk_level`. At level 1, descriptions get loopier. At
  level 2, the parser starts "mishearing" the player (intentional typos in
  echoed input). At level 3, the player blacks out and wakes up in `brig` or
  `sickbay`. Drinking ordinary water is fine.

### Parser conventions

- Verbs match first; then noun phrases are resolved against visible items, NPCs,
  and inventory (in that order).
- Aliases live on the data structure (`NPC.aliases`, `Item.aliases`); the parser
  does not hard-code synonyms.
- Unknown input gets a tonally appropriate failure ("Frak if I know what that
  means, specialist.") rather than a sterile "I don't understand."
- The parser is dumb on purpose. No NLP. Tokenize, lowercase, match.

---

## Conventions for future work

- Engine code: minimal, generic, no BSG references. Should be reusable for any
  parser game.
- Content code: all the BSG flavor lives here. When in doubt, ask: is this thing
  generic interactive-fiction machinery, or is it specifically about Galactica?
  That tells you which directory it belongs in.
- **Never `print()` or `input()` in engine or content code.** Always go through
  the session's `IO` object. This is what keeps local and networked play sharing
  the same code path.
- Tests cover the parser, world state mutations, save/load round-trip, and at
  least one test that runs two concurrent sessions against the server and
  confirms they don't bleed into each other. We do not unit-test jokes.
- Save format is versioned. If we change `WorldState` shape, bump `version` and
  write a migration.
- Saves are written atomically (tmp + fsync + rename) and live at a stable
  on-disk path so they survive host reboot.
- Python 3.11+. Standard library only for the engine (incl. `asyncio` for the
  server); content can do whatever.
