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


def previous_log_file() -> Path:
    """The log from the run before this one.

    A failure at startup used to erase its own evidence: the log is rewritten
    every launch, so restarting to find out what went wrong was the one action
    guaranteed to destroy the answer.
    """
    return log_file().parent / "aurix-previous.log"


def llama_log() -> Path:
    """Where the model server writes its own log, next to Aurix's."""
    return log_file().parent / "llama.log"
