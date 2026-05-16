# BALANCE.md

Comprehensive stat-change audit for the hardening pass.

**Stat range:** `[0, 100]` for all four (`morale`, `suspicion`, `cylon_vibes`,
`exhaustion`). Helper `bump_stat()` clamps; you cannot push past either bound.

**Legend:**
- **one-shot** — gated by a flag, fires the first time only
- **repeatable** — bumps every time, no cap on calls
- **per-turn** — bumps with the turn tick

---

## Verb-level

| Action | Δ morale | Δ suspicion | Δ cylon_vibes | Δ exhaustion | Repeat? | Notes |
|---|---:|---:|---:|---:|---|---|
| `salute` | -3 | | | | repeatable | also `dignity_lost +1`; free of turn cost? No — burns a turn |
| `frak` | **+1** (post-tune) | | | | repeatable | burns a turn (+1 ex implicit) |
| `wait` | | **-1** (post-tune, cap 0) | | | repeatable | "lay low" — see tuning notes |
| any turn-advancing | | | | +1 | per-turn | implicit; via session tick |

## Items

| Action | Δ morale | Δ suspicion | Δ cylon_vibes | Δ exhaustion | Repeat? | Notes |
|---|---:|---:|---:|---:|---|---|
| `eat algae_bar` | -2 | | | -3 | **one-shot** | item consumed |
| `use mop` | -3 | **-1** (post-tune) | | +4 | repeatable | core suspicion-reducer; player can grind, but exhausts |
| `use locker` | | | +2 | | one-shot | déjà vu via "dent without a story" |
| `use console` | -2 | | | +2 | repeatable | sets `noticed_anomaly` flag |
| `drink canteen` (filled) | +5 | +8 | | -5 | repeatable | bumps `tigh_drink_count` |
| `drink flask` | +6 | +2 | | +6 | repeatable | bumps `tigh_drink_count` |
| `drink stash_bottle_mess` | +6 | +2 | | +6 | repeatable | bumps `tigh_drink_count` |
| `drink stash_bottle_hangar` | +6 | +2 | | +6 | repeatable | bumps `tigh_drink_count` |
| `examine photo_academy` | | +20 | | | one-shot | the iconic spike |
| `use cigarette` | +6 | | | +4 | one-shot | item consumed |
| `use cylon_detector` | -5 (if points at player) | | +10 (if points at player) | | repeatable, random | ~30% chance points at player |
| `use sealed_envelope` | | | | | one-shot | triggers `forbidden_knowledge` ending |

## Rooms — on_enter

| Room | First visit | Revisit | Notes |
|---|---|---|---|
| env_control | (intercom page, no stat) | — | |
| corridor_c12 | random encounter, see below | random encounter | encounter stat bumps **one-shot per type** (post-tune) |
| head_deck_5 | suspicion **+10** (witness Tigh) | — | via `witness_once` |
| mess_hall | (jump gossip flag) | random encounter (no stat) | |
| corridor_b | random encounter, see below | random encounter | encounter stat bumps **one-shot per type** (post-tune) |
| pilots_rec | morale +3 | — | |
| baltars_lab | suspicion +5 (witness), morale -3, cylon_vibes +2 | (nothing post-tune; was morale -1) | revisit damper removed |
| hangar_deck | random encounter (no stat) | random encounter (no stat) | |
| corridor_a | morale +2 | — | "officer country carpet" |
| sickbay | (no stat) | — | |
| adamas_quarters | suspicion **+15** (witness) | — | the "moment" |
| brig | cylon_vibes +8 | **(no stat post-tune)** | was +2 on revisit |
| observation_deck | (no stat) | — | |
| cic | morale +4, suspicion +3 | — | "you snuck in" / "you're on camera" |
| algae_processor | morale -10, cylon_vibes -3 | — | mystery meat reveal |
| adamas_workshop | suspicion +15 | — | second photo + workshop |
| storage_bay | cylon_vibes **+10** | **(no stat post-tune)** | was +10 every entry |

### Corridor C-12 random encounters (one-shot per type, post-tune)

| Encounter | Δ suspicion | Δ morale | Δ cylon_vibes | Notes |
|---|---:|---:|---:|---|
| `tigh_staggers` | +4 | | | one-shot |
| `starbuck_punches` | | +2 | | one-shot |
| `six_walks` | | | +5 | one-shot, also `saw_a_six` flag |
| `baltar_argues` | +3 | -1 | | one-shot |
| `apollo_mopes` | | +1 | | one-shot |
| `tyrol_yells` | | | | (no bump) |

### Corridor B-7 random encounters (one-shot per type, post-tune)

| Encounter | Δ suspicion | Δ morale | Δ cylon_vibes | Notes |
|---|---:|---:|---:|---|
| `six_supervisor` | | | +8 | one-shot |
| `six_distant` | | | +3 | one-shot |
| `tigh_catwalk` | +5 | | | one-shot |
| `pilots_yelling` | | +1 | | one-shot |
| `ensign_lost` | | | | (no bump) |

## NPC `talk` — default (each call)

| NPC | Δ morale | Δ suspicion | Δ cylon_vibes | Notes |
|---|---:|---:|---:|---|
| `hadrian` | +2 | | | repeatable; fraternizing |
| `tigh` | -2 | | | repeatable; intimidating |
| `adama` | -2 | | | repeatable; formal |
| `starbuck` | +4 | | | repeatable; chaos |
| `apollo` | +3 | | | repeatable; himbo energy |
| `baltar` | -2 | | | repeatable; he drains |
| `six` | | | +25 | each call also re-checks cylon ending |
| `roslin` | +1 | **+1** (post-tune, was +3) | | repeatable but small |
| `tyrol` | +1 | | | repeatable |
| `boomer` | | | +2 | repeatable; ambient creepy |
| `helo` | +2 | | | repeatable; bumps `romance_helo` |
| `gaeta` | +2 | | | repeatable; uses player's NAME |
| `cottle` | +1 | | | repeatable |
| `dualla` | +1 | | | repeatable |
| `cook` | -1 | | | repeatable |

## NPC `talk` — topic-specific (additional, on top of default)

| Topic | Δ | Repeat? | Notes |
|---|---|---|---|
| `tigh about adama/bill/water/flask/meeting/quarters` | suspicion +25 | repeatable | 3 asks → spaced ending |
| `roslin about prophecy` | — | one-shot (starts quest) | |
| `roslin about yes` | suspicion +12 | one-shot | wrong answer |
| `roslin about no` | morale -5 | one-shot | also wrong |
| `roslin about maybe` | suspicion +8, morale -3 | one-shot | also wrong |
| `starbuck about cards` | morale +3 | one-shot | starts cards quest |
| `starbuck about triad` | morale +5 | one-shot | |
| `starbuck about arm/wrestle` | morale +3, exhaustion +5 | one-shot | she dislocates something |
| `starbuck about making out` | morale +10, romance bump | one-shot per beat | beat 1/2/3 → complicated |
| `starbuck about graceful` | morale +5 | one-shot | cards outcome |
| `starbuck about flirt` | morale +7, romance bump | one-shot | cards outcome |
| `starbuck about cheat` | morale -15, suspicion +12 | one-shot | public humiliation |
| `starbuck about accuse` | morale +6, romance terminal | one-shot | "we respect each other too much" |
| `baltar about her` | suspicion +8, cylon_vibes +12 | one-shot | play-along |
| `baltar about nobody` | suspicion +12, morale -3 | one-shot | call-out |
| `baltar about juno` | suspicion +3 | repeatable | sets `baltar_distracted` |
| `six about god/love` | cylon_vibes +35 | repeatable | romance bump |
| `six about cylon` | cylon_vibes +30 | repeatable | |
| `six about anything else (default topics)` | cylon_vibes +25 | repeatable | |
| `boomer about water/home/the music/being someone else` | cylon_vibes +18 to +25 | repeatable | "honest" answers spike |
| `boomer about no/nothing/etc` | morale +1 | repeatable | "dismissive" answers safe |
| `boomer about cylon` | cylon_vibes +10 | repeatable | |
| `dualla about apollo/self/hypothetically` | morale, romance bump | one-shot per beat | her flirty topics |
| `dualla about boomer` | cylon_vibes +4 | repeatable | she suspects |
| `roslin about napkin` | — | repeatable (after `prophecy` started) | hints toward Adama |
| `tyrol about boomer` | cylon_vibes +3 | repeatable | |

## Quest rewards

| Action | Δ | Notes |
|---|---|---|
| `give wrench to tyrol` | morale +8, suspicion **-10** (post-tune, was -5) | one-shot |
| `give flask/thermos/grease_can to tigh` (intermediate) | suspicion +4 | per delivery |
| 3rd stash bottle returned to Tigh | morale +8, exhaustion +6 | one-shot (full quest) |

## Stash bottle / photo / detector / cigarette discoveries

| Action | Δ | Notes |
|---|---|---|
| `examine loose tile` (head) | suspicion +5 | one-shot — flask appears |
| `examine kitchen` (mess) | suspicion +5 | one-shot — thermos appears |
| `examine raptor` (hangar) | suspicion +5 | one-shot — grease can appears |
| `examine drawer` (adama's qtrs) | — | one-shot — photo appears |

## Ambient (random fire, low probability)

| Entry | Δ | Notes |
|---|---|---|
| Watchtower callable | cylon_vibes +6 | per fire |
| All-Along callable | cylon_vibes +5 | per fire |
| All other ambient strings | — | flavor only |

## Endings & their triggers

| Ending | Trigger | Notes |
|---|---|---|
| `hero` | give napkin to adama AND realized_napkin_is_coords AND suspicion < 75 AND exhaustion < 80 | |
| `spaced` (via Tigh) | suspicion ≥ 75 + next talk to tigh | |
| `spaced` (global) | suspicion = 100 anywhere | session loop check |
| `spaced` (via Adama refusing napkin) | give napkin to adama AND suspicion ≥ 75 | Adama hands you to MPs |
| `cylon_love_triangle` | cylon_vibes ≥ 75 + next talk to six | |
| `love_quadrangle` | 3rd unique romance NPC bumped while 2 already active | quadrangle ending |
| `forbidden_knowledge` | `use sealed_envelope` | one-shot |
| collapse → sickbay | exhaustion = 100 | not an ending, a setback |

---

## Identified balance issues + tuning plan

### Critical: Promotion Material was unreachable

**Problem:** Hero ending requires visiting `head_deck_5` (`witness_once` +10
suspicion) and entering `cic` first time (+3 suspicion). Floor of +13 even on
a perfect run. Random corridor encounters compound on every re-visit. The
only suspicion-reducer was `give wrench to tyrol` (-5). Net: impossible to
finish Hero with suspicion = 0.

**Tuning:**
1. **Corridor encounter stat bumps become one-shot per encounter type.** The
   encounter still fires for narrative (Tigh staggers past, Six walks by,
   etc.) but stat consequences only register the first time you witness that
   specific event. Re-traversing corridors no longer compounds.
2. **`give wrench to tyrol` reward: suspicion -10** (was -5). The Chief is a
   powerful ally; making it worth more.
3. **`use mop` now reduces suspicion -1** (per use, cap at 0). Doing your
   actual job lowers your profile. Tradeoff: each mop is also -3 morale and
   +4 exhaustion, so grinding has a real cost.
4. **`wait` now reduces suspicion -1** (per call, cap at 0). "Lay low for a
   shift." Tradeoff: each `wait` is +1 exhaustion via the turn tick.
5. **`talk to roslin` default suspicion: +1** (was +3). Still draws attention
   for being seen with the President but doesn't compound brutally.

**Result:** Promotion Material now reachable. Path: avoid all sensitive Tigh
topics, avoid Baltar's lab, avoid examining the photo, avoid Roslin entirely
(or only briefly), do the wrench quest for -10, then grind a few mops to
clear the +13 floor.

### Repeatable maxers that drive a stat to bound trivially

- **Storage bay revisits:** were +10 cylon_vibes EVERY entry. **Tuned to
  one-shot.** Eight entries would max cylon_vibes from 0.
- **Brig revisits:** were +2 cylon_vibes per revisit. **Removed.** First
  entry stays +8.
- **Baltar's lab revisits:** were -1 morale per revisit (compounded with
  default talk's -2). **Removed revisit damper.** First entry's -3 morale
  stands.
- **`frak`:** was +2 morale per call. **Tuned to +1.** Still cathartic but
  doesn't grind morale to 100 in 25 turns.

### Self-limiting "maxers" left alone

- **Stash bottle drinks** (+6 morale each, REPEATABLE, no consumption):
  technically maxes morale in 9 drinks, but also +6 exhaustion each →
  unconsumable after ~14 drinks (collapse). Self-limiting through exhaustion.
- **NPC talk repeats** (+2 to +4 morale each): self-limiting because each
  talk advances a turn (+1 exhaustion).
- **Tigh sensitive topics** (+25 each, REPEATABLE): the entire mechanic is
  that 3 asks → spaced. Working as designed.
- **Six default talks** (+25 cylon_vibes each): 3 talks → cylon love
  triangle ending. Working as designed.

---

## What was listed but isn't implemented

These items were mentioned in the hardening prompt as things to harden, but
they don't exist as systems in this codebase:

- **Time of day / schedules** — no clock; turns are abstract.
- **Duty roster assignments** — no scheduled work tasks; quests are
  player-initiated.
- **`IS_CYLON`** — no boolean Cylon-or-not flag for the player; only the
  `cylon_vibes` stat suggests it.
- **Resurrection count / resurrection during a timed quest** — no resurrect
  mechanic; death = ending.

These weren't tested in the harness. If the intent was to add them as part
of hardening, they would be new features and weren't built per the
"no new features" constraint.

---

## Harness run results

The harness was a 30-test suite covering all 7 ending variants, all 5 side
quests start-to-finish, four systems-collide cases, the `hint` verb at every
flag state, and full WorldState save/load round-tripping.

**Final status: 195/195 tests passing.** Was 166 before this pass.

### Bugs surfaced by the harness

The harness caught **two real engine bugs** that the per-system tests had
missed:

1. **`cmd_load` did not restore `visited_rooms` or `stats`.** The load
   handler iterated a hardcoded list of attribute names that hadn't been
   updated when `visited_rooms` (added in the room-density pass) and
   `stats` (added in the stats overhaul) were introduced. Loading a save
   from a long playthrough silently truncated the player's visited-room
   list to `[current_room]` and reset all four hidden stats to defaults.
   Fixed in [engine/commands.py](engine/commands.py); the list is now
   commented as load-bearing so future fields don't silently break loads.

2. **Item alias collision: the canteen claimed `flask` as an alias.** When
   the new flask item was added for the stash quest, the canteen kept its
   old `flask` alias from when `flask` was the in-universe name for the
   canteen. `give flask to tigh` resolved to the canteen, not the flask,
   silently breaking the stash quest's three-bottle return chain. Fixed in
   [content/items.py](content/items.py); the canteen now only answers to
   `canteen`.

Both bugs were invisible to existing per-system tests because those tests
manipulate state directly rather than driving the parser through a full
sequence. The harness's end-to-end playthroughs caught them.

### Tuning verification

- **Promotion Material is reachable.** The test
  `test_promotion_material_reachable_via_tuning` simulates a mid-hero-run
  state (suspicion 13 = head witness +10, CIC entry +3, the natural floor)
  and confirms that `give wrench to tyrol` (-10) plus 3 mop uses (-3)
  cleanly bring suspicion to exactly 0 before the napkin handoff. Hero
  ending fires; achievement unlocks. **Reachable but requires deliberate
  play** — exactly what was asked for.

- **All 7 ending variants reachable end-to-end** through full playthroughs
  (the harness drives each from the opening room, not from pre-set state):
  - HERO via napkin → Adama
  - SPACED via Tigh dialogue (3 sensitive topics)
  - SPACED via global suspicion = 100 (`set_stat` + turn tick)
  - SPACED via Adama refusing the napkin at suspicion ≥ 75
  - CYLON LOVE TRIANGLE via Six dialogue
  - LOVE QUADRANGLE via 3rd unique flirtation
  - FORBIDDEN KNOWLEDGE via opening the CIC envelope

- **All 5 side quests complete from intro to resolution:**
  - Tigh's Stash — find all 3 bottles, return all 3, get the swig
  - Missing Wrench — Baltar misdirection (`talk about juno`) + pickup +
    return to Tyrol
  - Cards Night — each of the 4 outcomes (graceful/flirt/cheat/accuse)
    distinct and resolved
  - Mystery Meat — algae processor reveal sets the solved flag
  - Prophecy — yes/no/maybe each register their own choice flag

- **Systems-collide cases:**
  - Collapse mid-stash-quest preserves the napkin (lose canteen/mop/algae
    bar but the macguffin survives)
  - Quadrangle pre-empts the hero path even when player is in CIC with
    realized napkin
  - Forbidden knowledge ending fires even with active romance
  - Cylon-vibes pumped via Boomer can carry into a Six interaction that
    triggers the love triangle
  - Three sensitive Tigh topics overrides the canteen quest

- **`hint` verb fires correct guidance at 4 distinct flag states** (no
  quest → head; canteen but no napkin → floor/tile; napkin but no
  realization → bridge/Roslin; realized but not in CIC → CIC).

### Full WorldState save/load round-trip

Verified that every documented field on `WorldState` round-trips through a
save → load cycle:

- `player_name`, `current_room`, `inventory`
- `room_items` (with complex per-room arrangements)
- `flags` (all keys: quest state, NG+ carryover, romance flags, witness
  one-shots, encounter one-shots, frak count, Tigh drink count)
- `turn`
- `npc_state` (nested per-NPC dicts including wrong-name counters,
  rumor indices, romance bumps, corridor last-encounter trackers)
- `visited_rooms`
- `stats` — all four (`morale`, `suspicion`, `cylon_vibes`, `exhaustion`)

A meta-test (`test_world_state_has_no_undocumented_fields`) sentinels the
set of WorldState fields. **If a future change adds a field, this test
fails and prompts you to also update the save/load `cmd_load` attribute
list and the full-state round-trip coverage.** This is the cheapest way to
prevent the cmd_load bug from recurring.

Achievements are written to `<save_dir>/<player>/achievements.json`
**outside** the world save and persist across world reloads.

### Re-tune summary

Final stat-change deltas (re-applied from the table above for quick
reference):

| Knob | Before | After | Why |
|---|---:|---:|---|
| `frak` morale bump | +2 | **+1** | trivial maxer otherwise |
| `wait` suspicion bump | (none) | **-1** | enables Promotion Material |
| `mop` suspicion bump | (none) | **-1** | enables Promotion Material |
| `give wrench to tyrol` suspicion | -5 | **-10** | enables Promotion Material |
| `talk roslin` default suspicion | +3 | **+1** | compounded too brutally on repeat talks |
| Corridor C-12 encounter stat bumps | every visit | **one-shot per encounter type** | re-traversal compounded |
| Corridor B-7 encounter stat bumps | every visit | **one-shot per encounter type** | re-traversal compounded |
| Storage bay re-entry cylon_vibes | +10 every entry | **first entry only** | trivial maxer |
| Brig re-entry cylon_vibes | +2 each | **(removed)** | trivial maxer |
| Baltar's lab re-entry morale | -1 each | **(removed)** | could grind to 0 |

---

*Final report: 195/195 tests passing. README "Known Bugs" line preserved
as "So say we all." See section above for the only bugs that did surface
— both fixed in this pass.*

