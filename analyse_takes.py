"""Re-analyse already recorded takes without making anyone speak again."""

import sys
import wave
from pathlib import Path

import numpy as np

from tune_timing import TAKES_DIR, analyse

names = sys.argv[1:] or [p.stem for p in sorted(Path(TAKES_DIR).glob("*.wav"))]

for name in names:
    path = Path(TAKES_DIR) / f"{name}.wav"
    with wave.open(str(path), "rb") as handle:
        raw = np.frombuffer(handle.readframes(handle.getnframes()), dtype=np.int16)
    analyse(name, raw.astype(np.float32) / 32767.0)
