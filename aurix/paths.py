"""Locating Aurix's files, whether running from source or installed."""

import os
import sys
from pathlib import Path


def app_root() -> Path:
    """The folder Aurix's files live in."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def resolve(relative: str) -> Path:
    """Turn a path from config into a real one."""
    return app_root() / relative


def log_file() -> Path:
    """The log, in a writable folder rather than beside the exe."""
    folder = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Aurix"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "aurix.log"


def llama_log() -> Path:
    """Where the model server writes its own log, next to Aurix's."""
    return log_file().parent / "llama.log"
