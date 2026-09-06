"""Check that everything is wired up, without needing anyone to speak.

Lists the microphones, loads the speech model, and runs a silent clip through
it to prove the pipeline holds together.
"""

import time

import numpy as np
import sounddevice as sd

from gab import config, speech, tray
from gab.audio import record_until_silence  # noqa: F401  (import must not fail)

print("--- microphones ---")
default_input = sd.default.device[0]
for index, device in enumerate(sd.query_devices()):
    if device["max_input_channels"] > 0:
        marker = "  <-- default" if index == default_input else ""
        print(f"{index}: {device['name'][:50]}{marker}")

print("\n--- tray icon ---")
tray.create(on_quit=lambda icon: None)
print("built ok")

print("\n--- speech model ---")
started = time.perf_counter()
speech.load()
print(f"loaded in {time.perf_counter() - started:.1f}s")

print("\n--- transcribing one second of silence ---")
silence = np.zeros(config.SAMPLE_RATE, dtype=np.float32)
started = time.perf_counter()
result = speech.transcribe(silence)
print(f'got "{result}" in {time.perf_counter() - started:.2f}s')

print("\nALL CHECKS PASSED")
