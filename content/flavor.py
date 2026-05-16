"""Ambient events that fire between turns at low probability."""

from engine.events import register_ambient
from engine.world import bump_stat


AMBIENT_LINES = [
    # --- Baltar muttering past ---
    "From somewhere down the corridor, Dr. Baltar's voice rises in furious whispered argument with no one in particular. The argument loses. Baltar storms off, also alone.",
    "Baltar walks past in a hurry, gesturing with both hands at empty space. He doesn't see you. The empty space, possibly, does.",
    "Somewhere, Baltar is laughing at his own joke. You did not hear the joke. The laughter is going on for a worrying length of time.",

    # --- Intercom paging the dead ---
    "INTERCOM: 'PAGING LIEUTENANT BREN TO SICKBAY. PAGING LIEUTENANT BREN.' (Lieutenant Bren has been dead since the first attack. Nobody has updated the rosters. Nobody ever will.)",
    "INTERCOM: 'CAPTAIN PROSNA, REPORT TO HANGAR DECK.' (Captain Prosna died at Kobol. The intercom does not know. The intercom does not learn.)",
    "INTERCOM: 'CHAPLAIN ELOSHA TO CIC.' There is a long pause. The intercom seems to reconsider. The intercom does not retract.",
    "INTERCOM: 'WILL THE OWNER OF A BROWN DUFFEL PLEASE REMOVE IT FROM THE HANGAR DECK. IT IS LEAKING.' There is no further information about the duffel. There will be no further information about the duffel.",
    "INTERCOM: 'PETTY OFFICER PEROFSKI TO COMMS.' (You don't know if Perofski is dead. The way the intercom said it, neither does Perofski.)",

    # --- Pilot crying in a corner ---
    "A pilot you don't recognize is sitting on a deck plate, crying into the visor of their helmet. You walk past. They prefer it that way.",
    "Through an open doorway you glimpse a pilot in flight gear, holding a photograph in both hands and weeping silently. They will be dead by act three. Statistically.",
    "A pilot walks past whistling. You don't recognize the tune. You will hear it again.",

    # --- Distant gunfire ---
    "From a deck below, three short bursts of small-arms fire. Then silence. Then nervous laughter. Then more silence.",
    "Distant gunfire from the training deck. Or possibly not training. Nobody has gone to investigate.",

    # --- Tigh visibly drunk on a catwalk ---
    "On a catwalk overhead, Colonel Tigh sways slightly while saluting a fire suppression panel with crisp precision. He maintains the salute for an admirable length of time.",
    "Through a deck grating, you spot Colonel Tigh on a catwalk, having a long whispered conversation with what appears to be a coffee maker. The coffee maker is taking it well.",

    # --- Officers abruptly hushing ---
    "Two officers stop talking abruptly when you enter. They were definitely talking about Adama. The slightly older one says 'we'll continue this in MY quarters' in a tone that is, frankly, suggestive.",
    "An ensign and a captain in mid-conversation pause as you walk past. They wait. You walk further. They resume in a different language.",

    # --- Banal texture ---
    "A specialist in the next corridor over is singing the Colonial Anthem off-key. They go silent when an officer passes. They resume when the officer is gone. The officer pretends not to notice.",
    "The deck plate under your feet vibrates briefly. FTL spool-up? Cylons? The mess hall ice cream machine kicking on? Impossible to say.",
    "A Raptor pre-flight alarm sounds two corridors away. Nobody seems to react. The alarm seems embarrassed.",
    "A coolant leak two corridors over is being fixed by someone you have never met but who has, by reputation, fixed every coolant leak on this ship for nine years. They are not on the roster. You suspect they are a ghost. The coolant suspects nothing.",
    "A maintenance bot rolls past in the opposite direction. The bot has no eyes. The bot does not need to look at you. The bot has, somehow, judged you.",
    "Someone, somewhere, drops a clipboard. There is no follow-up sound. The clipboard, you suspect, has been absorbed.",

    # --- Surreal ---
    "For one full second, every clock on this deck reads 1900 exactly. Then they don't. Nobody else seems to have noticed.",
    "Your reflection in the polished bulkhead waves. You did not.",
    "Four notes hum from somewhere. They might be a ventilation duct. They might be in your head. The ventilation duct is, when you check, not on.",
    "A door at the end of the corridor opens. A door at the end of the corridor closes. Nobody walked through either time. The door is, you note, still closed when you look at it.",

    # --- Melodramatic ---
    "Apollo, somewhere overhead, sighs loud enough to be tactical.",
    "Starbuck's voice carries from a deck below, mid-shout. The word 'FRAK' is recognizable. The other six words are not.",
    "Two pilots making out in an alcove see you and don't stop. They wave. They go back to it. You move on.",
]


# Callable ambient: music nobody else hears, plus a stat bump.
def _watchtower(world):
    bump_stat(world, "cylon_vibes", 6)
    return (
        "A melody surfaces in the back of your head. Four notes. Then four more. "
        "You don't recognize it. You don't recognize ever NOT recognizing it. The "
        "melody continues for several seconds. Somewhere on the ship, you feel "
        "absolutely certain, three other people are humming it right now."
    )


def _all_along(world):
    bump_stat(world, "cylon_vibes", 5)
    return (
        "You catch yourself humming. Something you don't know. You stop. You start "
        "again. You stop. It is unclear which of these is voluntary."
    )


def _watchtower_cylon_only(world):
    """Cylon-only ambient. Returns None for non-Cylon players (events.tick
    handles None as a no-fire). Registered multiple times so Cylon players
    see Watchtower-themed ambients ~3x as often."""
    if not world.flags.get("is_cylon"):
        return None
    bump_stat(world, "cylon_vibes", 3)
    return (
        "The melody is in your head again. Four notes. Four more. You know — you\n"
        "don't know HOW you know — it's called 'All Along the Watchtower.' You\n"
        "have never heard it. It has always been there."
    )


def install() -> None:
    register_ambient(*AMBIENT_LINES)
    register_ambient(_watchtower, _all_along)
    # Three copies so that, when an ambient fires for a Cylon player, the
    # Cylon-only variant has substantially higher selection probability.
    register_ambient(_watchtower_cylon_only, _watchtower_cylon_only, _watchtower_cylon_only)
