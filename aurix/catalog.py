"""The models and voices you can pick from in the settings window.

Model sizes are the real byte counts from Hugging Face. A finished download
that does not match is a truncated file, so it gets thrown away rather than
loaded. Voices have no size because they all live in one file that ships with
the app.
"""

from dataclasses import dataclass
from pathlib import Path

from . import config, paths, settings

MODEL_REPO = "https://huggingface.co/unsloth/Qwen3.5-{size}-GGUF/resolve/main/{file}"


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
    """One of Kokoro's voices. They all live in the one file, so unlike a model
    there is nothing to download and nothing to be the right size."""

    key: str  # what Kokoro calls it
    name: str
    note: str


def _model(size: str, file: str, name: str, note: str, byte_count: int) -> Model:
    return Model(
        key=file,
        name=name,
        note=note,
        filename=file,
        url=MODEL_REPO.format(size=size, file=file),
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

# Kokoro ships 54, most of them other languages. These are the English ones
# worth offering. Aurix's own voice is built on Heart - the robot filter was
# tuned against it - so the others will sound a little different under it.
VOICES = [
    Voice("af_heart", "Heart", "American, female. What Aurix sounds like."),
    Voice("af_bella", "Bella", "American, female."),
    Voice("af_nicole", "Nicole", "American, female. Softer."),
    Voice("af_nova", "Nova", "American, female."),
    Voice("am_puck", "Puck", "American, male."),
    Voice("am_fenrir", "Fenrir", "American, male. Deeper."),
    Voice("bf_emma", "Emma", "British, female."),
    Voice("bm_george", "George", "British, male."),
]


def models_folder() -> Path:
    """Where models are kept. Changeable, because they are big."""
    return Path(settings.get("models_folder"))


def model_file(model: Model) -> Path:
    return models_folder() / model.filename


def kokoro_files() -> tuple[Path, Path]:
    """The voice engine and the voices, which ship with the app."""
    return paths.resolve(config.KOKORO_MODEL), paths.resolve(config.KOKORO_VOICES)


def is_installed(item) -> bool:
    """For a model, present and the right size. Every voice is in the one file,
    so a voice is installed exactly when that file is there."""
    if isinstance(item, Model):
        path = model_file(item)
        return path.exists() and path.stat().st_size == item.size
    return all(path.exists() for path in kokoro_files())


def _chosen(items, key):
    """Whichever is set, or the first one when the setting names something that
    is not here any more.

    Upgrading from a version before Kokoro leaves a Piper voice saved in
    settings.json, and a name nobody recognises should not stop Aurix starting.
    """
    return next((item for item in items if item.key == key), items[0])


def chosen_model() -> Model:
    return _chosen(MODELS, settings.get("model"))


def chosen_voice() -> Voice:
    return _chosen(VOICES, settings.get("voice"))
