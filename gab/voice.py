"""The voice that reads answers aloud.

Piper runs on the processor, so it needs no graphics card and nothing is sent
anywhere. A medium-quality voice generates speech about thirty times faster
than it plays, which is why the whole answer is made in one go rather than
sentence by sentence - the extra machinery would buy a fraction of a second.
"""

import numpy as np
import sounddevice as sd
from piper import PiperVoice

from . import config, paths, settings

_voice: PiperVoice | None = None


def load() -> None:
    """Load the voice up front, so the first answer is not slow."""
    global _voice
    _voice = PiperVoice.load(paths.resolve(config.VOICE_MODEL))


def speak(text: str) -> None:
    """Read text aloud. Returns once it has finished speaking."""
    if _voice is None:
        raise RuntimeError("voice.load() must be called before speak()")
    if not text.strip():
        return

    chunks = list(_voice.synthesize(text))
    if not chunks:
        return

    audio = np.concatenate(
        [np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16) for chunk in chunks]
    )

    volume = settings.get("volume")
    if volume < 1.0:
        audio = (audio * volume).astype(np.int16)

    sd.play(audio, chunks[0].sample_rate)
    sd.wait()


def stop() -> None:
    """Cut the speech off part way through."""
    sd.stop()
