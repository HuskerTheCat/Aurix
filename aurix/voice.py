"""Reading answers aloud, with Kokoro, on the processor.

Speaking is the slowest part of answering, so it starts on the first finished
sentence rather than waiting for the whole reply. Kokoro makes speech at about
3.6x realtime here, so a first sentence lands in well under a second and the
pre-rendered "hmm" covers even that.

Everything goes through robot.py on the way out, which is what makes it sound
like Aurix rather than like a person. That includes the fillers, or the noises
it makes while thinking would be in a different voice from the answer.

Measure with the process pinned to the P-cores. Left alone, Windows drifts the
work onto the E-cores part way through and this drops to 0.7x without warning.
"""

import queue
import random
import re
import threading
import time

import numpy as np
import sounddevice as sd
from kokoro_onnx import Kokoro

from . import catalog, config, robot, settings

# A sentence ends at punctuation followed by a space. "3.5" has no space, so
# it survives; "Mr. Smith" does not, which is a gap nobody has noticed yet.
_SENTENCE = re.compile(r"(?<=[.!?])\s+")

# Said the moment a question lands, so nothing sits in silence while the model
# thinks. Rendered at startup and kept in memory, so saying one costs nothing.
FAST_FILLERS = ["Hmm.", "Let me think.", "One second.", "Right."]
FUN_FILLERS = [
    "Lemme think about that.",
    "Gimme a sec.",
    "Ooh, good one.",
    "Alright, let's see.",
]

# Both sets are made at startup so switching mode costs nothing later. It is
# the first thing you hear every single time, so it is worth the extra second
# of loading.
FILLERS = FAST_FILLERS + FUN_FILLERS

_engine: Kokoro | None = None
_talking: "Speech | None" = None
_fillers: dict = {}
_speaking = 0.0  # how loud it is right now, for the face
_playing = False  # cleared by stop(), so following the loudness lets go early


def load() -> None:
    """Load the voice engine. Every voice is in it, so this is done once."""
    global _engine, _fillers
    model, voices = catalog.kokoro_files()
    if not model.exists():
        raise FileNotFoundError(f"voice engine missing: {model}")
    if not voices.exists():
        raise FileNotFoundError(f"voices missing: {voices}")
    _engine = Kokoro(str(model), str(voices))
    _fillers = {}


def warm_up() -> None:
    """First synthesis is slow, and the fillers have to be ready instantly."""
    global _fillers
    _say_it("Ready.", catalog.chosen_voice().key)
    _fillers = {line: _render(line) for line in FILLERS}


def filler():
    """A short noise to make while the answer is still being worked out."""
    if not _fillers:
        return None
    wanted = FUN_FILLERS if settings.get("fun_mode") else FAST_FILLERS
    return _fillers[random.choice(wanted)]


def speak(text: str) -> None:
    """Say something and wait. For the Test button and previews."""
    if _engine is None:
        raise RuntimeError("voice.load() must be called before speak()")
    _play(text, catalog.chosen_voice().key)


def preview(name: str, text: str) -> None:
    """Try a voice out without switching to it."""
    _play(text, name)


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
    global _playing
    _playing = False
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
            sound = item if isinstance(item, tuple) else _render(item)
            if sound is None:
                continue
            # stamped after making the audio, so it really is the first sound
            if self.started_at is None:
                self.started_at = time.perf_counter()
            _out(sound)


def _say_it(text: str, name: str):
    """Ask Kokoro for the words, slowed ready for robot.apply to speed them up."""
    return _engine.create(
        text, voice=name, speed=robot.SPEAK_SPEED, lang=config.KOKORO_LANGUAGE
    )


def _render(text: str, name: str | None = None):
    """Turn text into Aurix's voice. This is the slow part of speaking."""
    if not text.strip():
        return None

    samples, rate = _say_it(text, name or catalog.chosen_voice().key)
    if not len(samples):
        return None

    audio = robot.apply(samples.astype(np.float64), rate) * settings.get("volume")
    return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16), rate


def speaking_level() -> float:
    """0 to 1 while it is talking, so the mouth can move with it."""
    return _speaking


def _out(sound) -> None:
    """Play it, following the loudness as it goes so the face can lip sync."""
    global _speaking, _playing
    audio, rate = sound
    sd.play(audio, rate)
    _playing = True

    step = max(1, int(rate * 0.04))
    began = time.perf_counter()
    length = len(audio) / rate
    while _playing:
        elapsed = time.perf_counter() - began
        if elapsed >= length:
            break
        at = int(elapsed * rate)
        chunk = audio[at : at + step].astype(np.float32) / 32768.0
        _speaking = float(np.sqrt(np.mean(np.square(chunk)))) if chunk.size else 0.0
        time.sleep(0.03)

    _speaking = 0.0
    _playing = False
    sd.wait()


def _play(text: str, name: str) -> None:
    sound = _render(text, name)
    if sound is not None:
        _out(sound)
