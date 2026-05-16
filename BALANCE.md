# BALANCE.md

Comprehensive stat audit for the **second hardening pass** (post: critique
fixes, time system, schedules, duty roster, hunger, Cylon resurrection
mechanic, Quorum press conference).

**Stat range:** `[0, 100]` for all four (`morale`, `suspicion`, `cylon_vibes`,
`exhaustion`). Helper `bump_stat()` clamps; you cannot push past either bound.

**Legend:**
- **one-shot** — gated by a flag, fires the first time only
- **repeatable** — bumps every time, no cap on calls
- **per-turn** — bumps with the turn tick
- **per-shift** — bumps with shift-change hook

---

## Verb-level

| Action | Δ morale | Δ suspicion | Δ cylon_vibes | Δ exhaustion | Repeat? | Notes |
|---|---:|---:|---:|---:|---|---|
| `salute` | -3 | | | | repeatable | also `dignity_lost +1`; burns a turn |
| `frak` | +1 | | | | repeatable | burns a turn (per-tick +1 ex implicit) |
| `wait` | | -1 | | | repeatable | "lay low" — cap 0 |
| `sleep` | +2 | | | -100→0 | repeatable | advances 1 shift; fires shift-change hook |
| any turn-advancing | | | | +1 | per-turn | implicit; via session tick |

## Items

| Action | Δ morale | Δ suspicion | Δ cylon_vibes | Δ exhaustion | Repeat? | Notes |
|---|---:|---:|---:|---:|---|---|
| `eat algae_bar` | -2 | | | -3 | **one-shot** | item consumed |
| `use mop` | -3 | -1 | | +4 | repeatable | core suspicion-reducer; doubles as duty action |
| `use locker` | | | +2 | | one-shot | déjà vu via "dent without a story" |
| `use console` | -2 | | | +2 | repeatable | sets `noticed_anomaly`; doubles as `reroute_coolant` duty |
| `drink canteen` (filled) | +5 | +8 | | -5 | repeatable | `tigh_drink_count +1` |
| `drink flask`/`drink thermos`/`drink grease_can` | +6 | +2 | | +6 | repeatable | `tigh_drink_count +1` |
| `eat tray` (in mess, open) | -1 | | | -3 | **once/day** | sets `ate_today`; fails when mess closed |
| `examine photo_academy` | | +20 | | | one-shot | the iconic spike |
| `use cigarette` | +6 | | | +4 | one-shot | item consumed |
| `use cylon_detector` (non-Cylon, ~30% chance) | -5 | | +10 | | repeatable | random |
| `use cylon_detector` (Cylon, always) | -3 | | +5 | | repeatable | deterministic — always at player |
| `use commendation_letter` | +5 | -10 | | | one-shot | high-credibility press reward |
| `use sealed_envelope` | | | | | one-shot | triggers `forbidden_knowledge` ending |

## Rooms — on_enter (first visit)

| Room | Δ morale | Δ suspicion | Δ cylon_vibes | Notes |
|---|---:|---:|---:|---|
| env_control | | | | intercom page, no stat |
| corridor_c12 | (encounter) | (encounter) | (encounter) | **per-encounter-type one-shot** (post-rebalance) |
| head_deck_5 | | +10 | | `witness_once` Tigh drinking |
| mess_hall | | | | jump-gossip flag |
| corridor_b | (encounter) | (encounter) | (encounter) | **per-encounter-type one-shot** |
| pilots_rec | +3 | | | |
| baltars_lab | -3 | +5 (witness) | +2 | revisit damper removed |
| hangar_deck | | | | |
| corridor_a | +2 | | | "officer country carpet" |
| sickbay | | | | |
| adamas_quarters | | +15 | | `witness_once` "the moment" |
| brig | | | +8 | first entry only post-rebalance |
| observation_deck | | | | |
| cic | +4 | +3 | | "snuck in" / "on camera" |
| algae_processor | -10 | | -3 | mystery-meat reveal |
| adamas_workshop | | +15 | | the actual workshop |
| storage_bay | | | +10 | first entry only post-rebalance |

### Corridor encounters (one-shot per encounter type)

| Corridor | Encounter | Stat | Δ |
|---|---|---|---:|
| C-12 | tigh_staggers | suspicion | +4 |
| C-12 | starbuck_punches | morale | +2 |
| C-12 | six_walks | cylon_vibes | +5 |
| C-12 | baltar_argues | suspicion / morale | +3 / -1 |
| C-12 | apollo_mopes | morale | +1 |
| C-12 | tyrol_yells | — | — |
| B-7 | six_supervisor | cylon_vibes | +8 |
| B-7 | six_distant | cylon_vibes | +3 |
| B-7 | tigh_catwalk | suspicion | +5 |
| B-7 | pilots_yelling | morale | +1 |
| B-7 | ensign_lost | — | — |

## NPC `talk` — default (each call)

| NPC | Δ morale | Δ suspicion | Δ cylon_vibes |
|---|---:|---:|---:|
| `hadrian` | +2 | | |
| `tigh` (quest first time) | -2 | | |
| `adama` | -2 | | |
| `starbuck` | +4 | | |
| `apollo` | +3 | | |
| `baltar` | -2 | | |
| `six` | | | +25 |
| `roslin` | +1 | +1 | |
| `tyrol` | +1 | | |
| `boomer` | | | +2 |
| `helo` | +2 | | |
| `gaeta` | +2 | | |
| `cottle` | +1 | | |
| `dualla` | +1 | | |
| `cook` | -1 | | |

## NPC `talk` — topic-specific (additional)

| Topic | Δ | Notes |
|---|---|---|
| `tigh about adama/bill/water/flask/meeting/quarters` | suspicion +25 | 3 asks → spaced |
| `roslin about prophecy yes` | suspicion +12 | one-shot |
| `roslin about prophecy no` | morale -5 | one-shot |
| `roslin about prophecy maybe` | suspicion +8, morale -3 | one-shot |
| `roslin about press/conference/quorum/reporters` | (triggers minigame) | one-shot per run |
| `starbuck about cards` (Afternoon only) | morale +3 | starts cards quest |
| `starbuck about triad` | morale +5 | one-shot |
| `starbuck about arm/wrestle` | morale +3, exhaustion +5 | one-shot |
| `starbuck about making out` | morale +10, +romance | beat 1/2/3 |
| `starbuck about graceful` | morale +5 | cards outcome |
| `starbuck about flirt` | morale +7, +romance | cards outcome |
| `starbuck about cheat` | morale -15, suspicion +12 | cards outcome |
| `starbuck about accuse` | morale +6, romance terminal | cards outcome |
| `baltar about her` | suspicion +8, cylon_vibes +12 | play-along |
| `baltar about nobody` | suspicion +12, morale -3 | call-out |
| `baltar about juno` | suspicion +3 | sets `baltar_distracted` |
| `six about god/love` | cylon_vibes +35, romance | |
| `six about cylon` | cylon_vibes +30 | |
| `six about anything else` | cylon_vibes +25 | |
| `boomer about water/home/the music/being someone else` | cylon_vibes +18 to +25 | "honest" answers |
| `boomer about no/nothing` | morale +1 | dismissive (safe) |
| `boomer about cylon` | cylon_vibes +10 | |
| `dualla about apollo/self/hypothetically` | romance + small morale | |
| `dualla about boomer` | cylon_vibes +4 | |
| `tyrol about boomer` | cylon_vibes +3 | |

## Witness one-shots

| Witness | Δ | Source |
|---|---|---|
| First entry to head_deck_5 | suspicion +10 | Tigh drinking |
| First entry to adamas_quarters | suspicion +15 | unspoken bond |
| First entry to baltars_lab | suspicion +5 | Baltar arguing |
| First examine of `photo_academy` | suspicion +20 | the Picon photo |

## Quest rewards / completion

| Action | Δ | Notes |
|---|---|---|
| `give wrench to tyrol` | morale +8, suspicion **-10** | one-shot |
| `give flask/thermos/grease_can to tigh` (intermediate) | suspicion +4 | per delivery |
| 3rd stash bottle returned to Tigh | morale +8, exhaustion +6 | one-shot full quest |
| Duty completion (any chore) | morale -3, suspicion -5 | one per day |
| Romance "complicated" (any) | suspicion +5 | per romance |

## Time / shift system

| Trigger | Δ | Source |
|---|---|---|
| Every turn | exhaustion +1 | session tick |
| Shift change (every 15 turns) | (banner + cross-shift hooks) | auto |
| Day rollover, **duty skipped** | suspicion +5 | duties hook |
| Day rollover, **meal skipped** | exhaustion +6 | duties hook (hunger) |
| Exhaustion = 100 | collapse: items → env_control, ex → 30, room → sickbay | session |
| Suspicion = 100 | spaced ending (or Cylon resurrection) | session |

## Cylon mechanic (hidden)

| Trigger | Δ / Effect | Notes |
|---|---|---|
| `cylon_vibes` ≥ 75 | sets `is_cylon` silently | never surfaced to player |
| Cylon hits spaced/forbidden death | resurrect, NOT game-over | counts up |
| Resurrection 1 | npc_suspicious_hadrian = True | NPC drift |
| Resurrection 2 | npc_dead_helo = True | NPC drift |
| Resurrection 3 | Download Complete ending | replaces normal wake-up |
| Each resurrection | day +1, shift = 0, ex = 0, morale ÷ 2, sus ÷ 2 | drift |
| Cottle first talk while Cylon | (one-shot bloodwork warning) | text only |
| Watchtower Cylon-only ambient | cylon_vibes +3 (registered 3x for higher rate) | |

## Press conference (per-question deltas)

The minigame applies its own credibility-and-stat deltas per response. All
deltas are bounded (single-conference effects can't drive any stat past the
bound). Outcomes:

| Outcome | Δ morale | Δ suspicion | Reward |
|---|---:|---:|---|
| high (cred ≥ 70) | +10 | -5 | `commendation_letter` |
| medium (30 < cred < 70) | — | — | — |
| low (cred ≤ 30) | | +30 | sets `press_confirmed_conspiracies` |
| rock_bottom (cred ≤ 10) | -10 | +25 | sets `was_briefly_famous` |

Per-round honest answers raise suspicion by +3 to +15 depending on the
question. Political answers raise credibility +5 to +10 at -3 to -4 morale.
Unhinged answers have deterministic-per-`(player, day, question)` random
outcomes from a 2-3-entry pool, ranging from `+18 cred / +8 morale` to
`-25 cred / +12 suspicion`.

---

## Endings & triggers (8 total)

| Ending | Trigger | Cylon-affected? |
|---|---|---|
| `hero` | `give napkin to adama` + realized + sus<75 + ex<80 | NO — wins still win |
| `spaced` (Tigh dialogue) | sus≥75 + next Tigh talk | **YES — resurrects Cylons** |
| `spaced` (global threshold) | sus = 100 anywhere | **YES — resurrects Cylons** |
| `spaced` (Adama refusing napkin) | hero attempt with sus≥75 | **YES — resurrects Cylons** |
| `cylon_love_triangle` | cylon_vibes≥75 + Six talk | NO |
| `love_quadrangle` | 3rd unique romance bumped | NO |
| `forbidden_knowledge` | `use sealed_envelope` | **YES — resurrects Cylons** |
| `download_complete` | 3rd resurrection as Cylon | (it IS the Cylon ending) |

---

# SECOND HARDENING PASS — RESULTS

## Bugs found and fixed

### Latent soft-lock: collapse destroyed quest-relevant items

[engine/session.py](engine/session.py)'s `_check_collapse()` did:

```python
self.world.inventory.remove(item_id)
```

This destroyed the mop, canteen, and algae bar permanently. The mop is **not
respawned anywhere**, so a collapsed player whose roster duty for the day is
`mop_the_head` had no way to fulfill the duty — and the mop's general
suspicion-reducing role was lost forever.

**Fix:** changed `inventory.remove` → `move_item_to_room(world, item_id,
"env_control")`. Items now relocate to the player's bunk instead of being
destroyed. The narrative still reads "you are missing X" because they are,
in fact, no longer in the player's inventory — they just have to walk back
to env_control and take them.

Verified by `test_collapse_does_not_destroy_items_softlocking_mop_duty` and
`test_hunger_spiral_eventually_causes_collapse_but_not_softlock` in the new
harness file.

### `hint` verb didn't cover the new mechanics

The hint verb predates the time system, press conference, duty roster, and
Cylon mechanic. A player stuck mid-press-conference (which intercepts all
input) who typed `hint` would get the old generic fallback.

**Fix:** added a `press_active` branch at the top that returns:

> "A man at a podium chooses a path. There are three paths. None of them
> is the right path. Pick one anyway. (Type: honest, political, or unhinged.)"

And the catch-all fallback now lists: examine the duty roster in Corridor
C-12, eat in the mess at Morning or Afternoon, sleep if you're tired, wait
if you're paranoid.

## What turned out to be fine (audited but not changed)

- **`sleep` is not an exploit.** Sleep zeroes exhaustion but each sleep ALSO
  skips a meal and may skip your duty. Hunger penalty (+6 ex/day, fires at
  rollover) and missed-duty penalty (+5 sus/day) cap the strategy. A player
  sleep-spamming for ~16 days collapses; respawn cycle handles the rest.

- **Cylon resurrection cycle is bounded.** Each resurrection halves morale
  and suspicion, which superficially looks abusable — but the 3rd
  resurrection is the Download Complete ending, so the cycle terminates.
  Maximum suspicion-reduction available: floor → halve twice = ~×0.25.

- **Press conference can't be repeated.** Once you've completed (or
  rock-bottomed) one, Roslin refuses to send you again. No infinite source
  of commendation letters / suspicion reduction.

- **Duty completion is once-per-day.** Each chore has a `duty_*_today` flag
  that gates the reward. Skipping has a penalty. Players can't grind duties
  for unlimited suspicion reduction.

- **Repeatable NPC talks are self-limiting via turn tick.** Talking to
  Hadrian 30 times for +60 morale also costs 30 turns of exhaustion. Net
  effect: a tradeoff, not an exploit.

## Promotion Material reachability (re-verified)

The original Promotion Material achievement (complete a run with `suspicion = 0`)
was made reachable in the first hardening pass via wrench-quest reward (-10),
`use mop` (-1), `wait` (-1), and Roslin talk down to +1/talk. The
post-time-system additions make it EASIER, not harder:

- **Duty completion**: -5 sus per completed daily chore. With a roster cycle
  of 5+ days and 1 chore/day, a careful player can clear ~25 suspicion just
  by doing their actual job.
- **Wait verb**: -1 sus per call, unchanged.
- **Mop**: -1 sus per use, unchanged.

The hero path's natural suspicion floor is ~13 (head visit +10, CIC entry +3).
Wrench return alone clears that. With duty discipline, Promotion Material is
now substantially more accessible than before. Verified by
`test_promotion_material_reachable_via_tuning` (still green).

## Save/load round-trip — verified for all new subsystem state

The full-state save sentinel (`test_world_state_has_no_undocumented_fields`)
caught the addition of `shift`, `day`, `turns_this_shift` and is still
guarding `WorldState`. All other new state lives in `world.flags` (a generic
dict) and `world.npc_state` (nested dicts), both of which round-trip natively
through JSON.

**New comprehensive test** (`test_save_load_round_trips_every_new_subsystem_flag`)
asserts every Cylon, press, duty, hunger, NG+, romance, time, and stat flag
round-trips. Round-tripped fields verified:

- Time: `shift`, `day`, `turns_this_shift`
- Stats: all four
- Duty: `duty_today`, `duty_*_today`, `_last_rollover_day`, `_first_shift_change_done`
- Hunger: `ate_today`
- Cylon: `is_cylon`, `resurrection_count`, `npc_suspicious_hadrian`,
  `npc_dead_helo`, `cottle_bloodwork_warned`
- Press: `press_active`, `press_round`, `press_questions`, `press_credibility`,
  `was_briefly_famous`
- Romance: `active_romances`, `romance_*` for each NPC
- NG+: `ng_plus`, `ng_plus_count`, `previous_ending`
- Inventory, npc_state, visited_rooms (round-tripped via existing fields)

## Harness extension — systems-collide cases

The first hardening pass's harness covered the original 6 endings + 5 side
quests + a few collide cases. This pass added 14 new cross-system tests in
[tests/test_hardening_pass2.py](tests/test_hardening_pass2.py):

- Full Download Complete chain (3 resurrections from a Cylon start)
- Cylon state survives a mid-chain save/load
- Cylon player still HEROes (not all death endings are equal)
- Cylon player can still latrine-duty (Love Quadrangle isn't death)
- Press conference runs normally for a Cylon
- Press interception blocks `status`, `hint`, and other normal verbs
- Hint verb covers `press_active` (verified via `_hint_line` helper)
- Sleeping through a full day: skipped duty + skipped meal both penalize
- Hunger spiral eventually collapses without soft-locking
- The fixed collapse path: items relocate to env_control
- Comprehensive save/load with every subsystem's flag set
- Achievements use atomic write (no .tmp orphan)
- Sleep resets exhaustion but NOT suspicion
- Duty completion reduces suspicion independent of hunger penalty

## Test count and stability

Final test count: **298** across 13 files, **0 failed**, stable across 5
consecutive runs.

Categories:
- test_parser.py (19) — parser unit tests
- test_save.py (5) — save/load atomicity
- test_smoke.py (11) — opening quest flow
- test_endings.py (12) — per-system ending verification
- test_engine_features.py (6) — engine plumbing
- test_polish.py (21) — ambient / achievements / NG+ / deja-vu
- test_sidequests.py (31) — side quests + hidden rooms + envelope ending
- test_stats.py (29) — stat system
- test_romance.py (25) — romance state machine + new NPCs
- test_server.py (7) — LAN multiplayer server
- test_critique_fixes.py (13) — eight critique fixes from earlier
- test_harness.py (20) — playtest harness from first hardening pass
- test_full_state_save.py (10) — full WorldState round-trip
- test_time_system.py (30) — watch cycle, schedules, hunger, duty roster
- test_cylon_mechanic.py (26) — hidden Cylon mechanic + Download Complete
- test_press_conference.py (20) — Quorum Press Conference minigame
- **test_hardening_pass2.py (14)** — this pass

---

## What was *listed* in the original hardening prompts but never built

These keep appearing in the prompt examples but aren't actual systems in
this codebase:

- **Time of day** — exists now as the watch cycle.
- **Schedules** — exists now (`content/schedules.py`).
- **Duty roster assignments** — exists now (`content/duties.py`).
- **`IS_CYLON` flag** — exists now (`world.flags["is_cylon"]`).
- **Resurrection count** — exists now (`world.flags["resurrection_count"]`).

Everything the first hardening pass flagged as "not in the codebase" is now,
in fact, in the codebase. This pass confirms they all round-trip cleanly,
have proper test coverage, and don't introduce new soft-locks.

---

*Final report: 298/298 tests passing, stable. README "Known Bugs" line
preserved as "So say we all."*
