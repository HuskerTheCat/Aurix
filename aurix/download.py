"""Fetching a model file, with progress."""

import hashlib
import shutil
from pathlib import Path

import httpx

CHUNK = 1 << 20


class Cancelled(Exception):
    """Raised when the download was stopped on purpose."""


def fetch(url: str, destination: Path, size: int, sha256: str, on_progress,
          cancelled, on_checking=None) -> None:
    """Download to a .part file, then swap it in once it checks out.

    The hash is taken as it downloads rather than by reading the file back, so
    a 15 GB model is not read twice. Size is checked first because a truncated
    file is the likely failure and saying so is more use than "wrong hash".

    on_progress is called with bytes so far. cancelled is asked between chunks.
    on_checking, if given, is called once the bytes are in and the hash is
    being compared, which is not instant on a big file.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_name(destination.name + ".part")
    done = 0
    running = hashlib.sha256()

    try:
        with httpx.stream(
            "GET", url, follow_redirects=True, timeout=httpx.Timeout(60.0, connect=15.0)
        ) as reply:
            reply.raise_for_status()
            with part.open("wb") as out:
                for chunk in reply.iter_bytes(CHUNK):
                    if cancelled():
                        raise Cancelled
                    out.write(chunk)
                    running.update(chunk)
                    done += len(chunk)
                    on_progress(done)
    except BaseException:
        part.unlink(missing_ok=True)
        raise

    if part.stat().st_size != size:
        part.unlink(missing_ok=True)
        raise ValueError(f"{destination.name} came down the wrong size")

    if on_checking is not None:
        on_checking()
    if running.hexdigest() != sha256:
        part.unlink(missing_ok=True)
        raise ValueError(
            f"{destination.name} is the right size but not the right file, so "
            "it has not been kept"
        )

    destination.unlink(missing_ok=True)
    part.replace(destination)


def free_space(folder: Path) -> int:
    """Free bytes on whichever drive the folder is on, walking up if it is new."""
    existing = folder
    while not existing.exists():
        existing = existing.parent
    return shutil.disk_usage(existing).free
