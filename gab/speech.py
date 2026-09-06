"""Turn recorded audio into text."""

import numpy as np
from faster_whisper import WhisperModel

from . import config, paths

_model: WhisperModel | None = None


def load() -> None:
    """Load the model up front, so the first question is not slow."""
    global _model
    _model = WhisperModel(
        str(paths.resolve(config.WHISPER_MODEL)),
        device=config.WHISPER_DEVICE,
        compute_type=config.WHISPER_COMPUTE_TYPE,
    )


def transcribe(audio: np.ndarray) -> str:
    """Transcribe mono float32 audio recorded at config.SAMPLE_RATE."""
    if _model is None:
        raise RuntimeError("speech.load() must be called before transcribe()")

    segments, _info = _model.transcribe(audio, language="en", beam_size=1)
    real_speech = [
        segment.text.strip()
        for segment in segments
        if segment.no_speech_prob < config.NO_SPEECH_THRESHOLD
    ]
    return " ".join(real_speech).strip()
