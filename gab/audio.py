"""Microphone capture that stops on its own when you stop talking."""

from collections import deque

import numpy as np
import sounddevice as sd

from . import config


class NoSpeechDetected(Exception):
    """Nobody spoke before the timeout ran out."""


_threshold: float | None = None


def _level(block: np.ndarray) -> float:
    """Loudness of one block of audio, 0.0 to 1.0."""
    return float(np.sqrt(np.mean(np.square(block))))


def find_microphone() -> int | None:
    """Resolve config.MICROPHONE to a device index. None means system default."""
    if config.MICROPHONE is None:
        return None

    wanted = config.MICROPHONE.lower()
    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] > 0 and wanted in device["name"].lower():
            return index
    raise RuntimeError(f"no microphone matching {config.MICROPHONE!r}")


def _measure_room(stream, block_frames: int) -> float:
    """Sample the room so we know what background noise sounds like."""
    block_count = int(config.NOISE_CALIBRATION_SEC / config.BLOCK_SECONDS)
    levels = [_level(stream.read(block_frames)[0]) for _ in range(block_count)]
    return float(np.median(levels))


def calibrate() -> float:
    """Measure the room once at startup, so no request pays for it later."""
    global _threshold
    block_frames = int(config.SAMPLE_RATE * config.BLOCK_SECONDS)

    with sd.InputStream(
        samplerate=config.SAMPLE_RATE,
        channels=config.CHANNELS,
        dtype="float32",
        blocksize=block_frames,
        device=find_microphone(),
    ) as stream:
        room = _measure_room(stream, block_frames)

    _threshold = max(room * config.SPEECH_THRESHOLD_MULTIPLIER, config.MIN_SPEECH_LEVEL)
    return _threshold


def record_until_silence() -> np.ndarray:
    """Record from the microphone until the speaker goes quiet.

    Returns mono float32 audio at config.SAMPLE_RATE.
    Raises NoSpeechDetected if nobody speaks in time.
    """
    if _threshold is None:
        raise RuntimeError("audio.calibrate() must be called before recording")

    threshold = _threshold
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
            loud = _level(block) > threshold

            if not speaking:
                preroll.append(block)
                if loud:
                    speaking = True
                    collected.extend(preroll)
                elif elapsed > config.SPEECH_START_TIMEOUT_SEC:
                    raise NoSpeechDetected(
                        f"nothing louder than {threshold:.4f} in "
                        f"{config.SPEECH_START_TIMEOUT_SEC:.0f}s"
                    )
                continue

            collected.append(block)

            if loud:
                silence_for = 0.0
            else:
                silence_for += config.BLOCK_SECONDS
                if silence_for >= config.SILENCE_HANGOVER_SEC:
                    break

    return np.concatenate(collected).flatten()
