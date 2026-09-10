"""Locating Aurix's files, whether running from source or installed."""

import os
import sys
from pathlib import Path


def save_text(path: Path, text: str) -> None:
    """Write a small file so that a crash part way cannot leave it half written.

    Written beside itself and then renamed over the top, because the rename is
    the only step that has to be all-or-nothing. Writing straight over the real
    file means a crash, a power cut or a full disk halfway through leaves a
    truncated one - and settings.json, music.json and memory.txt are all files
    Aurix refuses to start without or quietly loses.

    Same shape as the .part file the model download already used.
    """
    beside = path.with_name(path.name + ".new")
    try:
        beside.write_text(text, encoding="utf-8")
        beside.replace(path)  # atomic on Windows for a same-folder rename
    except BaseException:
        beside.unlink(missing_ok=True)
        raise


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


def memory_file() -> Path:
    """The notes Aurix keeps about you, next to the settings it keeps for you."""
    return log_file().parent / "memory.txt"


def llama_log() -> Path:
    """Where the model server writes its own log, next to Aurix's."""
    return log_file().parent / "llama.log"
