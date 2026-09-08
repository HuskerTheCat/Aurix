"""How long the last request took, kept so the settings window can show it.

Measured in main.py, which is the only place that watches the whole thing from
microphone to speaker. The quiet gap is the interesting one - the time between
the question being understood and the first sound coming back, which is what
makes Aurix feel fast or slow.
"""

_last: dict = {}


def record(**parts) -> None:
    """Save the timings of the request that just finished, in seconds."""
    global _last
    _last = dict(parts)


def last() -> dict:
    """The last request's timings, or an empty dict before anything is asked."""
    return dict(_last)
