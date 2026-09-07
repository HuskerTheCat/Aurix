"""Fetching a model or voice file, with progress."""

import shutil
from pathlib import Path

import httpx

CHUNK = 1 << 20


class Cancelled(Exception):
    """Raised when the download was stopped on purpose."""


def fetch(url: str, destination: Path, size: int, on_progress, cancelled) -> None:
    """Download to a .part file, then swap it in once the size checks out.

    on_progress is called with bytes so far. cancelled is asked between chunks.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_name(destination.name + ".part")
    done = 0

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
                    done += len(chunk)
                    on_progress(done)
    except BaseException:
        part.unlink(missing_ok=True)
        raise

    if part.stat().st_size != size:
        part.unlink(missing_ok=True)
        raise ValueError(f"{destination.name} came down the wrong size")

    destination.unlink(missing_ok=True)
    part.replace(destination)


def fetch_small(url: str, destination: Path) -> None:
    """For the little settings file that rides along with a voice."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    reply = httpx.get(url, follow_redirects=True, timeout=30.0)
    reply.raise_for_status()
    destination.write_bytes(reply.content)


def free_space(folder: Path) -> int:
    """Free bytes on whichever drive the folder is on, walking up if it is new."""
    existing = folder
    while not existing.exists():
        existing = existing.parent
    return shutil.disk_usage(existing).free
