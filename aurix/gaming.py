"""Getting off the graphics card when something else wants it.

A game and a language model both want video memory, and the one that loses is
whichever asks second - either the model will not load, or the driver pushes
the game's textures out to system memory and the game stutters. So Aurix gets
out of the way: while something else is using the card, the model runs on the
processor instead and stays there until the card is free again.

It does not move back and forth per question. Moving back in while the game is
still holding the memory is the thing that causes the stutter, which is the
whole problem being avoided.

Costing it on this machine, 4B model, everything pinned to the fast cores:

    first word, short question   0.21s on the card   0.68s on the processor
    first word, search answer    0.17s               0.50 to 1.54s
    whole answer written         0.29s               1.98s

Generating is about seven times slower, but the model was never what you wait
for - the voice takes four and a half seconds to say a normal answer, and the
"hmm" covers the start. What it costs in practice is about half a second before
it starts talking.
"""

import time

from . import catalog, config, gpu, settings


def _model_wants_mb() -> float:
    """Video memory the chosen model needs, near enough.

    The file size, because a model buffer comes out within half a percent of it
    - the 4B is a 2777 MiB file and takes a 2766 MiB buffer. The headroom on
    top covers the context and compute buffers, which are a few hundred more.
    """
    return catalog.chosen_model().size / 1_048_576 + config.GAMING_HEADROOM_MB


def should_get_off(card_mb: float | None, on_the_card: bool) -> bool | None:
    """Whether the card is too busy for the model. None when it cannot tell.

    The rule scales itself to the machine: it is not "somebody is using 4 GB",
    it is "what is left would not fit the model". On a 16 GB card with a 3 GB
    model that needs something else to be using 12 GB before it triggers; on an
    8 GB card, 4 GB does it.
    """
    if not card_mb:
        return None

    in_use = gpu.in_use_mb()
    if in_use is None:
        return None

    wants = _model_wants_mb()
    # our own share is in that total, so take it out - otherwise a card only
    # just big enough for the model sees itself as the thing hogging it
    others = max(0.0, in_use - (wants if on_the_card else 0.0))
    return (card_mb - others) < wants


def chosen() -> str:
    """auto, on or off - what the settings window says."""
    return settings.get("gaming_mode")


class Decision:
    """Turns a stream of readings into a decision, slowly.

    Slowly on purpose. A game loading a level moves hundreds of megabytes
    around, and every switch is a model server restart, so a rule that reacted
    to one reading would spend the whole game restarting.
    """

    def __init__(self) -> None:
        self._wanted: bool | None = None
        self._since = 0.0

    def forget(self) -> None:
        """Start the count again.

        Used when the setting is not on automatic, so that turning automatic
        back on does not act on a single reading - the stale timestamp would
        otherwise look like it had been steady for hours.
        """
        self._wanted = None
        self._since = 0.0

    def update(self, reading: bool | None) -> bool | None:
        """Feed one reading. Returns a settled answer, or None if not settled."""
        if reading is None:
            return None

        if reading != self._wanted:
            self._wanted = reading
            self._since = time.monotonic()
            return None

        if time.monotonic() - self._since < config.GAMING_STEADY_SEC:
            return None
        return reading
