"""The settings a person is allowed to change.

config.py holds defaults and gets frozen into the executable, so nothing in it
can be changed after installing. Anything adjustable lives here instead, in a
small file next to the log, and the tray panel writes to it.
"""

import json
from typing import Any

from . import config, paths

# Only these can be changed from the panel. Everything else stays in config.
DEFAULTS: dict[str, Any] = {
    "microphone": config.MICROPHONE,  # None means whatever Windows is using
    "volume": 1.0,  # 0.0 to 1.0, applied to the spoken answer
    "wake_threshold": config.WAKE_THRESHOLD,
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
