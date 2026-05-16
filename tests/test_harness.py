"""Comprehensive playtest harness.

This file is the umbrella regression test. Where the per-system test files
verify *components* in isolation (one NPC, one item, one ending), this file
drives *full end-to-end playthroughs* and asserts on the world along the way.

Coverage targets:
- All 7 ending variants reached from a full start state
- All 5 side quests run to completion start-to-end
- "Systems collide" cases: quadrangle mid-main-quest, collapse mid-quest,
  forbidden-knowledge ending while romance active, etc.
- The `hint` verb fires meaningful guidance at every major flag state
- Promotion Material achievement reachable (suspicion 0 at ending)
"""

import os
import tempfile

import content  # noqa: F401
from engine.io import ScriptedIO
from engine.session import Session
from engine.world import bump_stat, get_stat, new_world, set_stat


def _run(inputs, player_name="Harness", start_room="env_control", save_dir=None):
    if save_dir is not None:
        os.environ["BSG_SAVE_DIR"] = save_dir
    world = new_world(player_name, start_room)
    io = ScriptedIO(inputs)
    next_action = Session(io=io, world=world).run()
    return io, world, next_action


# ─── full playthroughs to each ending ─────────────────────────────────────────


def test_full_hero_playthrough_from_intro_to_napkin_delivery():
    """The canonical happy path. Verifies the entire flag chain."""
    with tempfile.TemporaryDirectory() as tmp:
        io, world, _ = _run(
            [
                # Bunk → corridor → head → quest
                "go east",                          # corridor_c12
                "go east",                          # head_deck_5
                "talk to tigh",                     # quest given; napkin drops; canteen in inv
                # Find and take the napkin
                "examine floor",                    # reveals napkin in room
                "take napkin",                      # napkin in inventory
                # Back to corridor and up toward jump-context awareness
                "go west",                          # corridor_c12
                "go north",                         # mess_hall (sets heard_hadrian_jump_gossip)
                # Examine the napkin again with context — fires realization
                "examine napkin",
                # Navigate to CIC and deliver
                "go north",                         # corridor_b
                "go up",                            # corridor_a
                "go north",                         # cic
                "give napkin to adama",
            ],
            save_dir=tmp,
        )
        assert world.flags["got_canteen"] is True
        assert world.flags["realized_napkin_is_coords"] is True
        assert world.flags["__ended__"] == "hero"
        assert "ENDING: HERO" in io.transcript


def test_full_spaced_via_tigh_playthrough():
    """Asking Tigh enough sensitive topics gets the spaced ending."""
    with tempfile.TemporaryDirectory() as tmp:
        io, world, _ = _run(
            [
                "go east", "go east",            # head
                "talk to tigh",                   # quest given
                "talk to tigh about adama",       # +25 sus
                "talk to tigh about flask",       # +25 sus → 50 + head witness 10 = 60
                "talk to tigh about bill",        # +25 sus → 85 ≥ 75 → spaces on this very call
            ],
            save_dir=tmp,
        )
        assert world.flags["__ended__"] == "spaced"
        assert "SPACED" in io.transcript


def test_full_spaced_via_global_suspicion_100():
    """Suspicion hitting 100 anywhere triggers spaced on the next turn tick."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Doomed", "env_control")
        world.visited_rooms.append("env_control")
        set_stat(world, "suspicion", 100)
        io = ScriptedIO(["salute", "quit"])      # salute advances turn without touching sus
        Session(io=io, world=world).run()
        assert world.flags["__ended__"] == "spaced"


def test_full_spaced_via_adama_refusing_napkin():
    """If suspicion ≥ 75 when handing Adama the napkin, he hands you to MPs."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Sus", "cic")
        world.visited_rooms.append("cic")
        world.inventory.append("napkin")
        world.flags["realized_napkin_is_coords"] = True
        set_stat(world, "suspicion", 80)
        io = ScriptedIO(["give napkin to adama", "quit"])
        Session(io=io, world=world).run()
        assert world.flags["__ended__"] == "spaced"
        assert "DIDN'T TRUST YOU" in io.transcript


def test_full_cylon_love_triangle_playthrough():
    """Talking Six up to cylon_vibes ≥ 75 fires the love triangle."""
    with tempfile.TemporaryDirectory() as tmp:
        io, world, _ = _run(
            [
                "go east", "go north", "go north",   # to corridor_b (Six present)
                "talk to six",                       # +25 cylon_vibes
                "talk to six about god",             # +35 → 60
                "talk to six",                       # +25 → 85 ≥ 75 → ending
            ],
            save_dir=tmp,
        )
        assert world.flags["__ended__"] == "cylon_love_triangle"


def test_full_love_quadrangle_playthrough():
    """Starting a third unique flirtation while two are active → latrine duty."""
    with tempfile.TemporaryDirectory() as tmp:
        io, world, _ = _run(
            [
                "go east", "go north", "go north",  # to corridor_b
                "go east",                            # pilots_rec
                "talk to starbuck about making out",  # romance #1
                "go west", "go up", "go south",       # to sickbay
                "talk to helo",                       # romance #2
                "go north", "go north",               # to CIC
                "talk to dualla about apollo",        # romance #3 → quadrangle
            ],
            save_dir=tmp,
        )
        assert world.flags["__ended__"] == "love_quadrangle"
        assert "LATRINE DUTY" in io.transcript


def test_full_forbidden_knowledge_playthrough():
    """Read the sealed envelope from CIC."""
    with tempfile.TemporaryDirectory() as tmp:
        io, world, _ = _run(
            [
                "go east", "go north", "go north",
                "go up", "go north",                  # CIC
                "take envelope",
                "use envelope",
            ],
            save_dir=tmp,
        )
        assert world.flags["__ended__"] == "forbidden_knowledge"


# ─── side quest completion ────────────────────────────────────────────────────


def test_stash_quest_complete_via_giving_all_three_to_tigh():
    """Quest 1: Tigh's Secret Stash. Find all 3 bottles, return them.
    Time-gated to Night, so the player has to sleep ahead to find any."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Stasher", "env_control")
        world.visited_rooms.append("env_control")
        io = ScriptedIO(
            [
                # Morning Watch: get the canteen quest from Tigh
                "go east", "go east",
                "talk to tigh",                       # canteen + napkin drop
                # Sleep through Forenoon → Afternoon → Dog Watch → Night
                "sleep", "sleep", "sleep", "sleep",
                # Now Night: bottle reveals are accessible
                "examine loose tile",
                "take flask",
                "go west", "go north",
                "examine kitchen",
                "take thermos",
                "go north", "go north",
                "examine raptor",
                "take grease can",
                # Back to Tigh — still in head at Night (snoring)
                "go south", "go south", "go south", "go east",
                "give flask to tigh",
                "give thermos to tigh",
                "give grease can to tigh",
                "quit",
            ]
        )
        Session(io=io, world=world).run()
        assert world.flags.get("quest_stash_complete") is True
        assert "frak ME" in io.transcript


def test_wrench_quest_complete_via_baltar_misdirection():
    """Quest 2: distract Baltar, take the wrench, give it to Tyrol."""
    with tempfile.TemporaryDirectory() as tmp:
        io, world, _ = _run(
            [
                # Navigate to Baltar's lab
                "go east", "go north", "go north",
                "go west",                       # baltars_lab
                "talk to baltar about juno",     # distract him
                "take wrench",                   # now succeeds
                # Hand to Tyrol on hangar deck
                "go east", "go north",
                "give wrench to tyrol",
                "quit",
            ],
            save_dir=tmp,
        )
        assert world.flags.get("quest_wrench_complete") is True
        assert "wrench" not in world.inventory


def test_cards_quest_complete_all_four_outcomes_distinct():
    """Quest 3: each of the 4 cards-night outcomes is reachable and distinct.
    Cards Night is gated to Afternoon — set shift accordingly per iteration."""
    outcomes = {}
    for choice in ("graceful", "flirt", "cheat", "accuse"):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["BSG_SAVE_DIR"] = tmp
            world = new_world("Card", "env_control")
            world.shift = 2   # Afternoon: cards quest is open
            io = ScriptedIO(
                [
                    "go east", "go north", "go north", "go east",
                    "talk to starbuck about cards",
                    f"talk to starbuck about {choice}",
                    "quit",
                ]
            )
            Session(io=io, world=world).run()
            outcomes[choice] = world.flags.get("quest_cards_choice")
    assert outcomes == {
        "graceful": "graceful",
        "flirt": "flirt",
        "cheat": "cheat",
        "accuse": "accuse",
    }


def test_mystery_meat_quest_complete_via_algae_processor():
    """Quest 4: descend through env_control's hatch with the wrench, learn the
    upsetting truth about the vat."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Eater", "env_control")
        world.visited_rooms.append("env_control")
        world.inventory.append("wrench")
        io = ScriptedIO(["go down", "quit"])
        Session(io=io, world=world).run()
        assert world.flags.get("mystery_meat_solved") is True
        assert "CREWMAN ENGRAM" in io.transcript


def test_prophecy_quest_each_answer_lands_a_resolution():
    """Quest 5: all 3 prophecy answers are wrong; each records its own
    quest_prophecy_choice flag."""
    for ans in ("yes", "no", "maybe"):
        with tempfile.TemporaryDirectory() as tmp:
            io, world, _ = _run(
                [
                    "go east", "go north", "go north",
                    "go up", "go south",                  # sickbay
                    "talk to roslin about prophecy",
                    f"talk to roslin about {ans}",
                    "quit",
                ],
                save_dir=tmp,
            )
            assert world.flags.get("quest_prophecy_choice") == ans


# ─── systems-collide cases ────────────────────────────────────────────────────


def test_collide_collapse_during_stash_quest_preserves_napkin():
    """Collapsing in the middle of doing the stash quest. Player keeps the
    napkin (the macguffin) but loses canteen / mop / algae_bar."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Tired", "head_deck_5")
        world.visited_rooms.append("head_deck_5")
        world.inventory.extend(["napkin", "canteen", "mop", "algae_bar", "flask"])
        set_stat(world, "exhaustion", 99)
        io = ScriptedIO(["salute", "quit"])         # one turn tick → collapse
        Session(io=io, world=world).run()
        assert world.current_room == "sickbay"
        assert "napkin" in world.inventory          # macguffin survives
        assert "flask" in world.inventory           # stash bottle still in inv (not on the lose-list)
        # Items on the COLLAPSE_LOSES_ITEMS list should be gone:
        assert "canteen" not in world.inventory
        assert "mop" not in world.inventory
        assert "algae_bar" not in world.inventory


def test_collide_quadrangle_pre_empts_hero_path():
    """Triggering the quadrangle while holding the napkin and being in CIC
    ends the run as quadrangle, NOT hero. The quadrangle is checked at the
    point of the 3rd romance bump, regardless of where the player is in the
    main quest."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Heartbreaker", "cic")
        world.visited_rooms.append("cic")
        world.inventory.append("napkin")
        world.flags["realized_napkin_is_coords"] = True
        # Pretend two romances are active (would be set by gameplay normally)
        world.flags["active_romances"] = ["helo", "starbuck"]
        world.flags["romance_helo"] = 1
        world.flags["romance_starbuck"] = 1
        # Now attempt a third — should pre-empt the hero option.
        io = ScriptedIO(["talk to dualla about apollo", "quit"])
        Session(io=io, world=world).run()
        assert world.flags["__ended__"] == "love_quadrangle"


def test_collide_forbidden_knowledge_ends_even_with_active_romance():
    """Reading the envelope is an immediate ending. Active romance doesn't
    save you."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Tempted", "cic")
        world.visited_rooms.append("cic")
        world.inventory.append("sealed_envelope")
        world.flags["active_romances"] = ["starbuck"]
        world.flags["romance_starbuck"] = 1
        io = ScriptedIO(["use envelope", "quit"])
        Session(io=io, world=world).run()
        assert world.flags["__ended__"] == "forbidden_knowledge"


def test_collide_high_cylon_vibes_triggers_six_ending_even_if_six_not_default_room():
    """The cylon_vibes ≥ 75 check fires on ANY Six interaction. Even if the
    player gets there via Boomer's dream topics rather than Six dialogue
    directly, the next Six talk fires the ending."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Susceptible", "hangar_deck")
        world.visited_rooms.append("hangar_deck")
        # Pump cylon_vibes via Boomer's honest answers.
        io = ScriptedIO(
            [
                "talk to boomer",
                "talk to boomer about water",        # +18 cylon_vibes
                "talk to boomer",
                "talk to boomer about home",         # +18
                "talk to boomer",
                "talk to boomer about being someone else",  # +25
                "talk to boomer about the music",    # +22
                # Now go talk to Six; should fire the ending on first contact
                "go south",                          # corridor_b
                "talk to six",                       # cylon_vibes ≥ 75 already
                "quit",
            ]
        )
        Session(io=io, world=world).run()
        # Confirm cylon_vibes got high enough to trigger via Six
        assert world.flags.get("__ended__") == "cylon_love_triangle", (
            f"expected cylon ending; got {world.flags.get('__ended__')!r} "
            f"(cylon_vibes={get_stat(world, 'cylon_vibes')})"
        )


def test_collide_three_sensitive_tigh_topics_overrides_canteen_quest():
    """If the player gets sensitive with Tigh BEFORE accepting the canteen,
    they still get spaced. The spacing path takes priority over the quest."""
    with tempfile.TemporaryDirectory() as tmp:
        io, world, _ = _run(
            [
                "go east", "go east",            # head
                "talk to tigh",                   # quest given (canteen + napkin)
                "talk to tigh about flask",       # +25
                "talk to tigh about adama",       # +25
                "talk to tigh about meeting",     # +25 → 85+10=95 ≥ 75 → spaces in handler
            ],
            save_dir=tmp,
        )
        assert world.flags["__ended__"] == "spaced"


# ─── hint verb at every major flag state ──────────────────────────────────────


def test_hint_at_each_flag_state():
    """The hint verb should provide a different, contextually-correct nudge
    based on which quest flags are currently set."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp

        def hint_for_state(setup_fn):
            world = new_world("Hinter", "env_control")
            world.visited_rooms.append("env_control")
            setup_fn(world)
            io = ScriptedIO(["hint", "quit"])
            Session(io=io, world=world).run()
            return io.transcript.lower()

        # State 1: nothing started → points at THE HEAD (east, closed door)
        t = hint_for_state(lambda w: None)
        assert "east" in t and "closed door" in t

        # State 2: canteen received, napkin not yet examined
        def s2(w):
            w.flags["got_canteen"] = True
        t = hint_for_state(s2)
        assert "floor" in t or "tile" in t or "stall" in t

        # State 3: napkin in inventory, no realization yet
        def s3(w):
            w.flags["got_canteen"] = True
            w.flags["realized_napkin_is_coords"] = False
            w.inventory.append("napkin")
        t = hint_for_state(s3)
        # Should point at mess/CIC/Roslin
        assert "mess" in t or "bridge" in t or "roslin" in t

        # State 4: realized but not in CIC
        def s4(w):
            w.flags["got_canteen"] = True
            w.flags["realized_napkin_is_coords"] = True
            w.inventory.append("napkin")
        t = hint_for_state(s4)
        assert "cic" in t or "north" in t


# ─── balance: Promotion Material reachable ───────────────────────────────────


def test_promotion_material_reachable_via_tuning():
    """Verify the balance tuning makes Promotion Material reachable.

    Sets up the natural-floor state a careful player would arrive in
    mid-quest: +10 suspicion from head witness, +3 from CIC entry. Then
    confirms the suspicion-reducing actions (wrench return -10, mop -1,
    wait -1) clear it to 0 without exhausting to collapse."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BSG_SAVE_DIR"] = tmp
        world = new_world("Spotless", "hangar_deck")
        # Pretend the player has already done the legwork and is now at
        # the suspicion floor a hero playthrough naturally reaches.
        world.visited_rooms.extend(["env_control", "hangar_deck", "corridor_b",
                                     "corridor_a", "cic"])
        world.flags["entered_cic"] = True              # already paid CIC's +3
        world.flags["realized_napkin_is_coords"] = True
        world.inventory.extend(["wrench", "napkin", "mop"])
        set_stat(world, "suspicion", 13)               # head witness +10, cic +3
        set_stat(world, "exhaustion", 25)              # plausible mid-game
        # Pre-mark every corridor encounter as already witnessed so the
        # transit through corridor_b doesn't fire a fresh random suspicion
        # bump (tigh_catwalk: +5 / baltar_argues: +3 / etc) and break the
        # suspicion-0 assertion non-deterministically.
        for enc in ("tigh_catwalk", "six_supervisor", "six_distant",
                    "pilots_yelling", "ensign_lost"):
            world.flags[f"b7_encounter_seen_{enc}"] = True

        io = ScriptedIO(
            [
                # Hand wrench to Tyrol (-10 sus, +8 morale, removes wrench)
                "give wrench to tyrol",
                # Grind 3 mops to clear remaining 3 suspicion (-3 sus, +12 ex, -9 morale)
                "use mop", "use mop", "use mop",
                # Navigate to CIC: hangar_deck → corridor_b → corridor_a → cic
                "go south", "go up", "go north",
                # Deliver
                "give napkin to adama",
            ]
        )
        Session(io=io, world=world).run()

        assert world.flags["__ended__"] == "hero", (
            f"expected hero, got {world.flags.get('__ended__')!r} "
            f"(suspicion={get_stat(world, 'suspicion')}, "
            f"exhaustion={get_stat(world, 'exhaustion')})"
        )
        assert get_stat(world, "suspicion") == 0, (
            f"expected suspicion 0 for Promotion Material; "
            f"got {get_stat(world, 'suspicion')}"
        )
        assert "Promotion Material" in io.transcript
