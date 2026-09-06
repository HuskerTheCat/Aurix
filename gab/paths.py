"""Where Gab's files live, whether it is running from source or installed.

Packaged into an executable, everything sits beside the .exe. Running from
source, everything sits in the project folder. Either way the answer must not
depend on which directory the app happened to be started from - double-clicking
a shortcut can leave that pointing almost anywhere.
"""

import os
import sys
from pathlib import Path


def app_root() -> Path:
    """The folder Gab's files live in."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def resolve(relative: str) -> Path:
    """Turn a path from config into a real one."""
    return app_root() / relative


def log_file() -> Path:
    """Where to write the log. Not beside the exe - that may be read-only."""
    folder = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Gab"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "gab.log"
