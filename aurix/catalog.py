"""The models and voices you can pick from in the settings window.

Sizes are the real byte counts from Hugging Face. A finished download that does
not match is a truncated file, so it gets thrown away rather than loaded.
"""

from dataclasses import dataclass
from pathlib import Path

from . import paths, settings

MODEL_REPO = "https://huggingface.co/unsloth/Qwen3.5-{size}-GGUF/resolve/main/{file}"
VOICE_REPO = "https://huggingface.co/rhasspy/piper-voices/resolve/main/{path}"


@dataclass(frozen=True)
class Model:
    key: str
    name: str
    note: str
    filename: str
    url: str
    size: int


@dataclass(frozen=True)
class Voice:
    key: str
    name: str
    note: str
    filename: str
    url: str
    size: int


def _model(size: str, file: str, name: str, note: str, byte_count: int) -> Model:
    return Model(
        key=file,
        name=name,
        note=note,
        filename=file,
        url=MODEL_REPO.format(size=size, file=file),
        size=byte_count,
    )


def _voice(path: str, name: str, note: str, byte_count: int) -> Voice:
    file = path.rsplit("/", 1)[-1]
    return Voice(
        key=file,
        name=name,
        note=note,
        filename=file,
        url=VOICE_REPO.format(path=path),
        size=byte_count,
    )


MODELS = [
    _model(
        "2B", "Qwen3.5-2B-UD-Q4_K_XL.gguf",
        "Small (2B)", "Runs on nearly anything. Quick, but it gets things wrong.",
        1339752704,
    ),
    _model(
        "4B", "Qwen3.5-4B-UD-Q4_K_XL.gguf",
        "Medium (4B)", "What Aurix installs with. Fine for simple questions.",
        2912109728,
    ),
    _model(
        "9B", "Qwen3.5-9B-UD-Q4_K_XL.gguf",
        "Large (9B)", "Noticeably smarter. Wants a graphics card with 8 GB.",
        5966095584,
    ),
    _model(
        "27B", "Qwen3.5-27B-IQ4_XS.gguf",
        "Huge (27B)", "The good one. Wants a graphics card with 16 GB.",
        14977484704,
    ),
]

VOICES = [
    _voice(
        "en/en_GB/cori/high/en_GB-cori-high.onnx",
        "Cori", "British, female. Natural, but slower to start talking.", 114219352,
    ),
    _voice(
        "en/en_US/amy/medium/en_US-amy-medium.onnx",
        "Amy", "American, female. Quick.", 63201294,
    ),
    _voice(
        "en/en_US/lessac/high/en_US-lessac-high.onnx",
        "Lessac", "American, female. Very clear, but slower to start talking.", 113895201,
    ),
    _voice(
        "en/en_US/hfc_female/medium/en_US-hfc_female-medium.onnx",
        "Hannah", "American, female. Warmer and softer, and quick.", 63201294,
    ),
    _voice(
        "en/en_US/ryan/high/en_US-ryan-high.onnx",
        "Ryan", "American, male. Slower to start talking.", 120786792,
    ),
    _voice(
        "en/en_GB/alba/medium/en_GB-alba-medium.onnx",
        "Alba", "Scottish, female. Quick.", 63201294,
    ),
]


def models_folder() -> Path:
    """Where models are kept. Changeable, because they are big."""
    return Path(settings.get("models_folder"))


def voices_folder() -> Path:
    """Voices are small enough to leave beside the app."""
    return paths.resolve("runtime/voices")


def model_file(model: Model) -> Path:
    return models_folder() / model.filename


def voice_file(voice: Voice) -> Path:
    return voices_folder() / voice.filename


def is_installed(item) -> bool:
    """Installed means present and the right size."""
    path = model_file(item) if isinstance(item, Model) else voice_file(item)
    return path.exists() and path.stat().st_size == item.size


def find_model(key: str) -> Model:
    return next(model for model in MODELS if model.key == key)


def find_voice(key: str) -> Voice:
    return next(voice for voice in VOICES if voice.key == key)


def chosen_model() -> Model:
    return find_model(settings.get("model"))


def chosen_voice() -> Voice:
    return find_voice(settings.get("voice"))
