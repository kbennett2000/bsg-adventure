"""Ambient events that fire between turns at low probability."""

from engine.events import register_ambient


AMBIENT_LINES = [
    # Baltar muttering past
    "From somewhere down the corridor, Dr. Baltar's voice rises in furious whispered argument with no one in particular. The argument loses. Baltar storms off, also alone.",
    "Baltar walks past in a hurry, gesturing with both hands at empty space. He doesn't see you. The empty space, possibly, does.",

    # Intercom paging the dead
    "INTERCOM: 'PAGING LIEUTENANT BREN TO SICKBAY. PAGING LIEUTENANT BREN.' (Lieutenant Bren has been dead since the first attack. Nobody has updated the rosters. Nobody ever will.)",
    "INTERCOM: 'CAPTAIN PROSNA, REPORT TO HANGAR DECK.' (Captain Prosna died at Kobol. The intercom does not know. The intercom does not learn.)",
    "INTERCOM: 'CHAPLAIN ELOSHA TO CIC.' There is a long pause. The intercom seems to reconsider. The intercom does not retract.",

    # Pilot crying in a corner
    "A pilot you don't recognize is sitting on a deck plate, crying into the visor of their helmet. You walk past. They prefer it that way.",
    "Through an open doorway you glimpse a pilot in flight gear, holding a photograph in both hands and weeping silently. They will be dead by act three. Statistically.",

    # Distant gunfire
    "From a deck below, three short bursts of small-arms fire. Then silence. Then nervous laughter. Then more silence.",
    "Distant gunfire from the training deck. Or possibly not training. Nobody has gone to investigate.",

    # Tigh visibly drunk on a catwalk
    "On a catwalk overhead, Colonel Tigh sways slightly while saluting a fire suppression panel with crisp precision. He maintains the salute for an admirable length of time.",
    "Through a deck grating, you spot Colonel Tigh on a catwalk, having a long whispered conversation with what appears to be a coffee maker. The coffee maker is taking it well.",

    # Bonus ambient — texture
    "A specialist in the next corridor over is singing the Colonial Anthem off-key. They go silent when an officer passes. They resume when the officer is gone. The officer pretends not to notice.",
    "The deck plate under your feet vibrates briefly. FTL spool-up? Cylons? The mess hall ice cream machine kicking on? Impossible to say.",
    "A Raptor pre-flight alarm sounds two corridors away. Nobody seems to react. The alarm seems embarrassed.",
]


def install() -> None:
    register_ambient(*AMBIENT_LINES)
