"""Work out the right timing values from real recordings instead of guessing.

Records fixed-length takes so nothing can ever be cut off, finds where speech
actually ended using a proper voice-activity model, then replays each recording
against different silence settings to see which ones would have cut you off.

Run once, then we can re-test any number of settings against the saved audio
without you having to speak again.
"""

import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper.vad import VadOptions, get_speech_timestamps

from gab import config
from gab.audio import find_microphone

TAKE_SECONDS = 10.0
LEAD_IN_SECONDS = 2.0  # quiet time at the start, used to measure the room
CANDIDATE_HANGOVERS = [0.4, 0.5, 0.6, 0.7, 0.8, 1.0]
TAKES_DIR = Path("takes")

PROMPTS = [
    ("short", 'A short command, e.g. "what is the weather tomorrow"'),
    ("pause", 'A question with a real pause in the middle, e.g. "how long does it take... um... to drive to Denver"'),
    ("long", "A full sentence, then stop and stay quiet"),
]


def record_take(seconds: float) -> np.ndarray:
    frames = int(seconds * config.SAMPLE_RATE)
    audio = sd.rec(
        frames,
        samplerate=config.SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=find_microphone(),
    )
    sd.wait()
    return audio.flatten()


def save_wav(audio: np.ndarray, path: Path) -> None:
    path.parent.mkdir(exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(config.SAMPLE_RATE)
        handle.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())


def level_trace(audio: np.ndarray, block_frames: int) -> np.ndarray:
    usable = len(audio) // block_frames
    blocks = audio[: usable * block_frames].reshape(usable, block_frames)
    return np.sqrt(np.mean(np.square(blocks), axis=1))


def true_speech_bounds(audio: np.ndarray) -> tuple[float, float] | None:
    """Where speech really starts and ends, according to the voice model."""
    options = VadOptions(min_silence_duration_ms=100, speech_pad_ms=0)
    segments = get_speech_timestamps(audio, options, config.SAMPLE_RATE)
    if not segments:
        return None
    return (
        segments[0]["start"] / config.SAMPLE_RATE,
        segments[-1]["end"] / config.SAMPLE_RATE,
    )


def simulate_stop(trace: np.ndarray, threshold: float, hangover: float) -> float | None:
    """When the current recorder would have stopped, in seconds."""
    block = config.BLOCK_SECONDS
    speaking = False
    silence = 0.0
    for index, level in enumerate(trace):
        loud = level > threshold
        if not speaking:
            speaking = loud
            continue
        if loud:
            silence = 0.0
        else:
            silence += block
            if silence >= hangover:
                return (index + 1) * block
    return None


def analyse(name: str, audio: np.ndarray) -> None:
    block_frames = int(config.SAMPLE_RATE * config.BLOCK_SECONDS)
    trace = level_trace(audio, block_frames)

    lead_blocks = int(LEAD_IN_SECONDS / config.BLOCK_SECONDS)
    room = float(np.median(trace[:lead_blocks]))
    threshold = max(room * config.SPEECH_THRESHOLD_MULTIPLIER, config.MIN_SPEECH_LEVEL)

    bounds = true_speech_bounds(audio)
    print(f"\n=== take: {name} ===")
    print(f"room noise {room:.5f} | threshold {threshold:.5f} | peak {trace.max():.5f}")

    if bounds is None:
        print("no speech found in this take")
        return

    speech_start, speech_end = bounds
    print(f"speech ran {speech_start:.2f}s to {speech_end:.2f}s")
    print(f"{'hangover':>9} {'would stop':>11} {'verdict':>26}")

    for hangover in CANDIDATE_HANGOVERS:
        stop = simulate_stop(trace, threshold, hangover)
        if stop is None:
            print(f"{hangover:>8.1f}s {'never':>11} {'never stopped':>26}")
        elif stop < speech_end - 0.05:
            lost = speech_end - stop
            print(f"{hangover:>8.1f}s {stop:>10.2f}s {f'CUT OFF, lost {lost:.2f}s':>26}")
        else:
            print(f"{hangover:>8.1f}s {stop:>10.2f}s {f'ok, {stop - speech_end:.2f}s dead air':>26}")


def main() -> None:
    print(f"Recording {len(PROMPTS)} takes of {TAKE_SECONDS:.0f} seconds each.")
    print("Stay quiet for the first two seconds of each so the room can be measured.\n")

    for name, prompt in PROMPTS:
        print(f"--- {name}: {prompt}")
        for count in (3, 2, 1):
            print(f"    {count}...")
            time.sleep(1)
        print("    SPEAK NOW")
        audio = record_take(TAKE_SECONDS)
        save_wav(audio, TAKES_DIR / f"{name}.wav")
        print("    done")

    print("\n\n########## RESULTS ##########")
    for name, _prompt in PROMPTS:
        with wave.open(str(TAKES_DIR / f"{name}.wav"), "rb") as handle:
            raw = np.frombuffer(handle.readframes(handle.getnframes()), dtype=np.int16)
        analyse(name, raw.astype(np.float32) / 32767.0)


if __name__ == "__main__":
    main()
