"""Reading answers aloud, with Piper, on the processor.

Speaking is the slowest part of answering, so it starts on the first finished
sentence rather than waiting for the whole reply. A "high" voice runs at about
3x realtime and a "medium" one at about 12x, which is most of the difference
between a quick answer and an awkward pause.
"""

import queue
import random
import re
import threading
import time

import numpy as np
import sounddevice as sd
from piper import PiperVoice

from . import catalog, settings

# A sentence ends at punctuation followed by a space. "3.5" has no space, so
# it survives; "Mr. Smith" does not, which is a gap nobody has noticed yet.
_SENTENCE = re.compile(r"(?<=[.!?])\s+")

# Said the moment a question lands, so nothing sits in silence while the model
# thinks. Rendered at startup and kept in memory, so saying one costs nothing.
FILLERS = ["Hmm.", "Let me think.", "One second.", "Right."]

_voice: PiperVoice | None = None
_talking: "Speech | None" = None
_fillers: list = []


def load() -> None:
    """Load the chosen voice. Called again after you pick a different one."""
    global _voice, _fillers
    _voice = PiperVoice.load(catalog.voice_file(catalog.chosen_voice()))
    _fillers = []


def warm_up() -> None:
    """First synthesis is slow, and the fillers have to be ready instantly."""
    global _fillers
    list(_voice.synthesize("Ready."))
    _fillers = [_render(_voice, line) for line in FILLERS]


def filler():
    """A short noise to make while the answer is still being worked out."""
    return random.choice(_fillers) if _fillers else None


def speak(text: str) -> None:
    """Say something and wait. For the Test button and previews."""
    if _voice is None:
        raise RuntimeError("voice.load() must be called before speak()")
    _play(_voice, text)


def preview(path, text: str) -> None:
    """Try a voice out without switching to it."""
    _play(PiperVoice.load(path), text)


def whole_sentences(buffer: str) -> tuple[list[str], str]:
    """Finished sentences out of a growing answer, plus the unfinished tail."""
    parts = _SENTENCE.split(buffer)
    return parts[:-1], parts[-1]


def begin() -> "Speech":
    """Start speaking an answer that is still being written."""
    global _talking
    _talking = Speech()
    return _talking


def stop() -> None:
    """Cut the speech off part way through."""
    if _talking is not None:
        _talking.cancel()
    sd.stop()


class Speech:
    """Speaks sentences as they arrive, in order, on its own thread."""

    def __init__(self) -> None:
        self.started_at: float | None = None  # when the first sound came out
        self._waiting: queue.Queue = queue.Queue()
        self._cancelled = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def say(self, text: str) -> None:
        if text.strip():
            self._waiting.put(text)

    def say_sound(self, sound) -> None:
        """Play audio that is already made, for the instant reactions."""
        if sound is not None:
            self._waiting.put(sound)

    def finish(self) -> None:
        """Wait until everything queued has been spoken."""
        self._waiting.put(None)
        self._thread.join()

    def cancel(self) -> None:
        self._cancelled = True

    def _run(self) -> None:
        while True:
            item = self._waiting.get()
            if item is None or self._cancelled:
                return
            sound = item if isinstance(item, tuple) else _render(_voice, item)
            if sound is None:
                continue
            # stamped after making the audio, so it really is the first sound
            if self.started_at is None:
                self.started_at = time.perf_counter()
            _out(sound)


def _render(speaker: PiperVoice, text: str):
    """Turn text into audio. This is the slow part of speaking."""
    if not text.strip():
        return None

    chunks = list(speaker.synthesize(text))
    if not chunks:
        return None

    audio = np.concatenate(
        [np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16) for chunk in chunks]
    )

    volume = settings.get("volume")
    if volume < 1.0:
        audio = (audio * volume).astype(np.int16)

    return audio, chunks[0].sample_rate


def _out(sound) -> None:
    sd.play(*sound)
    sd.wait()


def _play(speaker: PiperVoice, text: str) -> None:
    sound = _render(speaker, text)
    if sound is not None:
        _out(sound)
