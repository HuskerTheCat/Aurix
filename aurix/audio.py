"""Microphone capture that stops on its own when you stop talking.

Whether a block is speech comes from Silero, the same voice model openWakeWord
already ships, not from how loud it is. Loudness cannot tell a voice from a
fan, so the room had to be measured at startup and any noise at that moment set
a bad threshold for the rest of the session. A voice model needs no measuring
and does not care how quiet the room is.
"""

from collections import deque

import numpy as np
import sounddevice as sd
from openwakeword.vad import VAD

from . import config, settings


class NoSpeechDetected(Exception):
    """Nobody spoke before the timeout ran out."""


_vad: VAD | None = None


def load() -> None:
    """Load the voice model, once, at startup."""
    global _vad
    _vad = VAD()


def _level(block: np.ndarray) -> float:
    """Loudness of one block, 0.0 to 1.0. Only used to make the face move."""
    return float(np.sqrt(np.mean(np.square(block))))


def _is_speech(block: np.ndarray) -> bool:
    """Whether a block sounds like somebody talking. Silero wants 16 bit PCM."""
    pcm = (block.flatten() * 32767).astype(np.int16)
    return _vad.predict(pcm, frame_size=len(pcm)) >= config.VAD_THRESHOLD


def microphones() -> list[tuple[int, str]]:
    """Every input device, as (index, name), for the picker in the panel."""
    return [
        (index, device["name"])
        for index, device in enumerate(sd.query_devices())
        if device["max_input_channels"] > 0
    ]


def find_microphone() -> int | None:
    """Which device to record from, or None for the Windows default.

    A chosen microphone is a preference, not a requirement: if it is missing,
    Aurix uses the default rather than refusing to start.
    """
    wanted = settings.get("microphone")
    if wanted is None:
        return None

    for index, name in microphones():
        if wanted.lower() in name.lower():
            return index

    print(f"  microphone {wanted!r} not found, using the system default")
    return None


def record_until_silence(on_level=None) -> np.ndarray:
    """Record from the microphone until the speaker goes quiet.

    on_level, if given, is called with the loudness of every block, so the
    face can move along with your voice.

    Returns mono float32 audio at config.SAMPLE_RATE.
    Raises NoSpeechDetected if nobody speaks in time.
    """
    if _vad is None:
        raise RuntimeError("audio.load() must be called before recording")

    # the model remembers what it just heard, and the tail of the last question
    # would otherwise count as somebody already talking
    _vad.reset_states()

    block_frames = int(config.SAMPLE_RATE * config.BLOCK_SECONDS)
    preroll_blocks = int(config.PREROLL_SEC / config.BLOCK_SECONDS)

    with sd.InputStream(
        samplerate=config.SAMPLE_RATE,
        channels=config.CHANNELS,
        dtype="float32",
        blocksize=block_frames,
        device=find_microphone(),
    ) as stream:
        preroll = deque(maxlen=preroll_blocks)
        collected = []
        speaking = False
        silence_for = 0.0
        elapsed = 0.0

        while elapsed < config.MAX_RECORDING_SEC:
            block, _overflow = stream.read(block_frames)
            elapsed += config.BLOCK_SECONDS
            if on_level is not None:
                on_level(_level(block))
            talking = _is_speech(block)

            if not speaking:
                preroll.append(block)
                if talking:
                    speaking = True
                    collected.extend(preroll)
                elif elapsed > config.SPEECH_START_TIMEOUT_SEC:
                    raise NoSpeechDetected(
                        f"no voice in {config.SPEECH_START_TIMEOUT_SEC:.0f}s"
                    )
                continue

            collected.append(block)

            if talking:
                silence_for = 0.0
            else:
                silence_for += config.BLOCK_SECONDS
                if silence_for >= settings.get("silence_hangover"):
                    break

    return np.concatenate(collected).flatten()
