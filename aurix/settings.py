"""User-changeable settings, stored outside the packaged app."""

import json
from pathlib import Path
from typing import Any

from . import config, paths

DEFAULTS: dict[str, Any] = {
    "microphone": config.MICROPHONE,
    "volume": 1.0,
    "wake_threshold": config.WAKE_THRESHOLD,
    "silence_hangover": config.SILENCE_HANGOVER_SEC,
    "think_out_loud": True,
    "model": Path(config.MODEL_PATH).name,
    "voice": config.VOICE,
    "models_folder": str(paths.resolve("runtime/models")),
    "theme": "midnight",
    "face": "protogen",
}

_values: dict[str, Any] = dict(DEFAULTS)


def _file():
    return paths.log_file().parent / "settings.json"


def load() -> None:
    """Read the file if it exists. Anything missing keeps its default."""
    global _values
    _values = dict(DEFAULTS)

    path = _file()
    if not path.exists():
        return

    stored = json.loads(path.read_text(encoding="utf-8"))
    _values.update({key: stored[key] for key in DEFAULTS if key in stored})


def get(name: str) -> Any:
    return _values[name]


def put(name: str, value: Any) -> None:
    """Change a setting and write it to disk straight away."""
    if name not in DEFAULTS:
        raise KeyError(f"unknown setting {name!r}")
    _values[name] = value
    _file().write_text(json.dumps(_values, indent=2), encoding="utf-8")
