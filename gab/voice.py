"""Reading answers aloud, with Piper, on the processor."""

import numpy as np
import sounddevice as sd
from piper import PiperVoice

from . import catalog, settings

_voice: PiperVoice | None = None


def load() -> None:
    """Load the chosen voice. Called again after you pick a different one."""
    global _voice
    _voice = PiperVoice.load(catalog.voice_file(catalog.chosen_voice()))


def speak(text: str) -> None:
    """Read text aloud. Returns once it has finished speaking."""
    if _voice is None:
        raise RuntimeError("voice.load() must be called before speak()")
    _play(_voice, text)


def preview(path, text: str) -> None:
    """Try a voice out without switching to it."""
    _play(PiperVoice.load(path), text)


def _play(speaker: PiperVoice, text: str) -> None:
    if not text.strip():
        return

    chunks = list(speaker.synthesize(text))
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
