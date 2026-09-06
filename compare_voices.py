"""Play the same answer in each candidate voice, so one can be picked by ear."""

import time

import numpy as np
import sounddevice as sd
from piper import PiperVoice

SAMPLE = (
    "The drive from Denver to Salt Lake City takes about seven and a half hours. "
    "It is currently fifty nine degrees and clear."
)

VOICES = [
    ("1", "en_US-ryan-high", "American man, highest quality"),
    ("2", "en_US-hfc_male-medium", "American man, faster medium quality"),
    ("3", "en_US-lessac-high", "American woman, the reference voice"),
    ("4", "en_GB-alan-medium", "British man"),
    ("5", "en_GB-cori-high", "British woman"),
]

for number, name, description in VOICES:
    voice = PiperVoice.load(f"runtime/voices/{name}.onnx")

    started = time.perf_counter()
    chunks = list(voice.synthesize(SAMPLE))
    audio = np.concatenate(
        [np.frombuffer(c.audio_int16_bytes, dtype=np.int16) for c in chunks]
    )
    generated = time.perf_counter() - started
    rate = chunks[0].sample_rate
    seconds = len(audio) / rate

    print(f"\n--- VOICE {number}: {name}  ({description})")
    print(f"    {seconds:.1f}s of speech generated in {generated:.2f}s"
          f"  ({seconds / generated:.1f}x faster than real time)")

    sd.play(audio, rate)
    sd.wait()
    time.sleep(0.7)

print("\ndone - which number sounded best?")
