"""Driving Spotify without an account.

Spotify's own API needs a sign-in and a Premium account to control playback, so
none of it is used. Songs are found with the same web search everything else
uses, and the resulting spotify: link is handed to the desktop app.

What it is doing is read off its window title, which is the song while it plays
and just "Spotify Premium" while it does not. That is the only way to tell
playing from paused, and without it pause and play are the same key.
"""

import ctypes
import os
import re
import threading
import time

from ddgs import DDGS

from . import keys

_SPOTIFY_ID = r"([A-Za-z0-9]{22})"
_LINKS = {
    "track": re.compile(rf"open\.spotify\.com/(?:intl-[a-z-]+/)?track/{_SPOTIFY_ID}"),
    "playlist": re.compile(rf"open\.spotify\.com/(?:intl-[a-z-]+/)?playlist/{_SPOTIFY_ID}"),
}

# Titles Spotify shows when nothing is playing.
_IDLE = {"spotify", "spotify premium", "spotify free"}

_START_TIMEOUT_SEC = 8.0
_POLL_SEC = 2.0
_SETTLE_SEC = 1.0

_queue: list[tuple[str, str]] = []
_lock = threading.Lock()
_playing_ours = ""  # the title of the track we started, so we know when it ends
_watcher: threading.Thread | None = None


# --- what Spotify is doing ---


def state() -> tuple[str, str]:
    """Returns ('playing'|'paused'|'closed', whatever is playing)."""
    title = _window_title()
    if title is None:
        return "closed", ""
    if title.strip().lower() in _IDLE:
        return "paused", ""
    return "playing", title.strip()


def _window_title():
    """Spotify's window title, or None when it is not running."""
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def look(window, _extra):
        if not user32.IsWindowVisible(window):
            return True
        if _process_name(window) != "spotify.exe":
            return True
        length = user32.GetWindowTextLengthW(window)
        if length:
            text = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(window, text, length + 1)
            found.append(text.value)
        return True

    user32.EnumWindows(look, None)
    return found[0] if found else None


def _process_name(window) -> str:
    """The exe behind a window, so other apps' windows are ignored."""
    pid = ctypes.c_ulong()
    ctypes.windll.user32.GetWindowThreadProcessId(window, ctypes.byref(pid))

    query_limited_information = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(
        query_limited_information, False, pid.value
    )
    if not handle:
        return ""
    try:
        path = ctypes.create_unicode_buffer(512)
        size = ctypes.c_ulong(512)
        if not ctypes.windll.kernel32.QueryFullProcessImageNameW(
            handle, 0, path, ctypes.byref(size)
        ):
            return ""
        return path.value.rsplit("\\", 1)[-1].lower()
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


# --- playing things ---


def play(request: str) -> str:
    """Play a song or playlist now, dropping anything queued behind it."""
    with _lock:
        _queue.clear()
    return _start(request)


def queue(request: str) -> str:
    """Play it now if nothing is on, otherwise line it up behind what is."""
    if state()[0] != "playing":
        return _start(request)

    found = _look_up(request)
    if found is None:
        return f"I could not find {request} on Spotify."

    with _lock:
        _queue.append(found)
        waiting = len(_queue)
    _start_watching()
    return f"Added {found[1]} to the queue." + (
        f" It is {waiting} songs away." if waiting > 1 else ""
    )


def _start(request: str) -> str:
    found = _look_up(request)
    if found is None:
        return f"I could not find {request} on Spotify."

    identifier, title = found
    kind = "playlist" if "playlist" in request.lower() else "track"
    _launch(kind, identifier)
    return f"Playing {title}."


def _launch(kind: str, identifier: str) -> None:
    """Open a spotify: link and wait until it is really playing.

    Spotify ignores the link entirely while it is already playing something, so
    it has to be stopped first. That was why asking for a song mid-playlist
    looked like it worked and then carried on with the wrong music.
    """
    global _playing_ours

    if state()[0] == "playing":
        keys.tap(keys.PLAY_PAUSE)
        time.sleep(_SETTLE_SEC)

    os.startfile(f"spotify:{kind}:{identifier}")
    _playing_ours = _settled_title()


def _look_up(request: str):
    kind = "playlist" if "playlist" in request.lower() else "track"
    name = re.sub(r"\bplaylists?\b", "", request, flags=re.IGNORECASE).strip()
    return _find(name, kind)


def _settled_title() -> str:
    """Wait for Spotify to actually start, so we know what we set going."""
    deadline = time.monotonic() + _START_TIMEOUT_SEC
    while time.monotonic() < deadline:
        playing, track = state()
        if playing == "playing":
            return track
        time.sleep(0.4)
    return ""


# --- the queue ---


def _start_watching() -> None:
    global _watcher
    if _watcher is not None and _watcher.is_alive():
        return
    _watcher = threading.Thread(target=_watch, daemon=True)
    _watcher.start()


def _watch() -> None:
    """Start the next queued song once Spotify moves off the one we started.

    Spotify carries on into something of its own choosing when a track ends, so
    "the title changed" is the signal that ours has finished.
    """
    while _queue:
        time.sleep(_POLL_SEC)
        playing, track = state()

        if playing == "closed":
            forget_queue()
            return
        if playing == "paused" or not track or track == _playing_ours:
            continue

        with _lock:
            if not _queue:  # cleared while we were waiting
                return
            identifier, _title = _queue.pop(0)
        _launch("track", identifier)


def skip() -> str:
    """Next song. Ours if any are waiting, otherwise whatever Spotify has."""
    with _lock:
        nothing_queued = not _queue
        if not nothing_queued:
            identifier, title = _queue.pop(0)

    if nothing_queued:
        keys.tap(keys.NEXT)
        return "Skipped."

    _launch("track", identifier)
    return f"Skipped to {title}."


def queued() -> list[str]:
    with _lock:
        return [title for _identifier, title in _queue]


def forget_queue() -> None:
    with _lock:
        _queue.clear()


# --- finding things ---


def _find(name: str, kind: str):
    """Turn a name into a Spotify id, using search rather than an account."""
    pattern = _LINKS[kind]
    found = []

    for result in DDGS().text(f"{name} site:open.spotify.com/{kind}", max_results=6):
        blob = " ".join(
            str(result.get(field) or "") for field in ("href", "title", "body")
        )
        match = pattern.search(blob)
        if match:
            found.append((match.group(1), _tidy(result.get("title") or name)))

    if not found:
        return None
    return max(found, key=lambda item: _closeness(name, item[1]))


# Given the choice, the plain studio recording is the one somebody means.
_QUALIFIERS = (
    "live", "remaster", "remix", "karaoke", "cover", "instrumental",
    "acoustic", "edit", "version", "demo", "tribute",
)


def _closeness(wanted: str, title: str) -> int:
    """How well a result matches, so "Fleetwood Mac" is not a song of that name.

    Asking for an artist should play one of theirs. Asking for a song should
    play that song. The only clue is which side of "by" the words landed on.
    """
    wanted = wanted.lower().strip()
    song, _, artist = title.lower().partition(" by ")

    if artist and wanted in artist:
        match = 3
    elif song.startswith(wanted):
        match = 2
    elif wanted in song:
        match = 1
    else:
        match = 0

    plain = 0 if any(word in song for word in _QUALIFIERS) else 1
    return match * 2 + plain


def _tidy(title: str) -> str:
    """Search results describe themselves oddly. Cut it back to song and artist."""
    title = title.split("|")[0]
    title = re.sub(r"\s*-\s*song and lyrics by\s*", " by ", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*-\s*songs? by\s*", " by ", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*-\s*playlist by\s*", " by ", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*[-|]\s*Spotify\s*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip(" -")
    return title[:80]
