"""Driving Spotify without an account.

Spotify's own API needs a sign-in and a Premium account to control playback, so
none of it is used. Songs are found with the same web search everything else
uses, and the resulting spotify: link is handed to the desktop app.

What it is doing is read off its window title, which is the song while it plays
and just "Spotify Premium" while it does not. That is the only way to tell
playing from paused, and without it pause and play are the same key.

Everything ends up a track link, because that is the only kind that starts
playing on its own. An album or playlist is turned into its first track and
Spotify carries on through the rest by itself.

Opening a link always brings Spotify to the front, so where its window was is
noted first and put back afterwards. Asking for a song should not take over the
screen.
"""

import ctypes
import json
import os
import re
import threading
import time

import httpx
from ddgs import DDGS

from . import keys, paths, search

_SPOTIFY_ID = r"([A-Za-z0-9]{22})"
_LINKS = {
    "track": re.compile(rf"open\.spotify\.com/(?:intl-[a-z-]+/)?track/{_SPOTIFY_ID}"),
    "album": re.compile(rf"open\.spotify\.com/(?:intl-[a-z-]+/)?album/{_SPOTIFY_ID}"),
    "playlist": re.compile(rf"open\.spotify\.com/(?:intl-[a-z-]+/)?playlist/{_SPOTIFY_ID}"),
}

# The word that picks the kind stays in the request until the search, since "the
# Rumours album" should find the album and "Rumours" on its own the song.
_KINDS = re.compile(r"\b(playlists?|albums?)\b", re.IGNORECASE)

# Titles Spotify shows when nothing is playing.
_IDLE = {"spotify", "spotify premium", "spotify free"}

_START_TIMEOUT_SEC = 8.0
_POLL_SEC = 2.0
_SETTLE_SEC = 1.0
_PAGE_TIMEOUT_SEC = 10.0

_queue: list[tuple[str, str]] = []  # track id, title
_lock = threading.Lock()
_playing_ours = ""  # the title of the track we started, so we know when it ends
_watcher: threading.Thread | None = None


# --- what Spotify is doing ---


def state() -> tuple[str, str]:
    """Returns ('playing'|'paused'|'closed', whatever is playing)."""
    window = _window()
    if window is None:
        return "closed", ""
    title = window[1]
    if title.strip().lower() in _IDLE:
        return "paused", ""
    return "playing", title.strip()


def _window():
    """Spotify's window and its title, or None when it is not running."""
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
            found.append((window, text.value))
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


# --- keeping it out of the way ---

_SW_MINIMIZE = 6


def _out_of_the_way() -> bool:
    """Whether Spotify is minimized or shut, so it can be put back that way."""
    window = _window()
    if window is None:
        return True
    return bool(ctypes.windll.user32.IsIconic(window[0]))


def _put_away() -> None:
    """Minimize Spotify. Windows then hands focus back to whatever was in front."""
    window = _window()
    if window is not None:
        ctypes.windll.user32.ShowWindow(window[0], _SW_MINIMIZE)


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

    _identifier, title = found
    with _lock:
        _queue.append(found)
        waiting = len(_queue)
    _start_watching()
    return f"Added {title} to the queue." + (
        f" It is {waiting} songs away." if waiting > 1 else ""
    )


def _start(request: str) -> str:
    found = _look_up(request)
    if found is None:
        return f"I could not find {request} on Spotify."

    identifier, title = found
    _launch(identifier)
    if not _playing_ours:
        # it never started, so whatever was remembered for this is no good
        _forget(_as_asked(request))
    return f"Playing {title}."


def _launch(identifier: str) -> None:
    """Open a track and wait until it is really playing.

    Spotify ignores the link entirely while it is already playing something, so
    it has to be stopped first. That was why asking for a song mid-playlist
    looked like it worked and then carried on with the wrong music.
    """
    global _playing_ours

    if state()[0] == "playing":
        keys.tap(keys.PLAY_PAUSE)
        time.sleep(_SETTLE_SEC)

    was_out_of_the_way = _out_of_the_way()
    os.startfile(f"spotify:track:{identifier}")
    _playing_ours = _settled_title()

    if was_out_of_the_way:
        _put_away()


def _look_up(request: str):
    """The track to play for a request - (id, title) - or None.

    Always a track, even for an album or a playlist, because a track link is the
    only one that starts playing by itself. Anything found once is remembered,
    so asking for it again skips the search.
    """
    asked = _as_asked(request)
    remembered = _recall(asked)
    if remembered is not None:
        return remembered

    kind = _kind_of(request)
    name = re.sub(r"\s+", " ", _KINDS.sub("", request)).strip()
    search.note_lookup(f"{name} on Spotify")

    found = _find(name, kind)
    if found is None:
        return None

    identifier, title = found
    if kind != "track":
        identifier = _first_track(kind, identifier)
        if identifier is None:
            return None

    _remember(asked, (identifier, title))
    return identifier, title


def _kind_of(request: str) -> str:
    """Which of Spotify's three kinds of link is being asked for."""
    found = _KINDS.search(request)
    if found is None:
        return "track"
    return "playlist" if found.group(1).lower().startswith("playlist") else "album"


def _first_track(kind: str, identifier: str):
    """The first track of an album or playlist, off its public embed page.

    Opening an album or playlist link only shows the page - it sits there and
    plays nothing. Starting its first track instead gets the whole thing, since
    Spotify carries on through the rest in order by itself.
    """
    page = httpx.get(
        f"https://open.spotify.com/embed/{kind}/{identifier}",
        follow_redirects=True,
        timeout=_PAGE_TIMEOUT_SEC,
    )
    page.raise_for_status()
    found = re.search(rf"spotify:track:{_SPOTIFY_ID}", page.text)
    return found.group(1) if found else None


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
        _launch(identifier)


def skip() -> str:
    """Next song. Ours if any are waiting, otherwise whatever Spotify has."""
    with _lock:
        nothing_queued = not _queue
        if not nothing_queued:
            identifier, title = _queue.pop(0)

    if nothing_queued:
        keys.tap(keys.NEXT)
        return "Skipped."

    _launch(identifier)
    return f"Skipped to {title}."


def queued() -> list[str]:
    with _lock:
        return [title for _identifier, title in _queue]


def forget_queue() -> None:
    with _lock:
        _queue.clear()


# --- remembering what was found ---
#
# The web search is the slow part of playing a song, a second or two before any
# sound comes out. People replay the same songs, so what a request turned out to
# mean is kept and the search skipped the next time it is asked for.

_CACHE_LIMIT = 500
_remembered: dict[str, list] | None = None


def _cache_file():
    return paths.log_file().parent / "music.json"


def _cache() -> dict:
    """The remembered requests, read from disk the first time one is needed."""
    global _remembered
    if _remembered is None:
        path = _cache_file()
        _remembered = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return _remembered


def _as_asked(request: str) -> str:
    """The form a request is remembered under, so case and spacing do not matter."""
    return re.sub(r"\s+", " ", request.strip().lower())


def _recall(asked: str):
    found = _cache().get(asked)
    return tuple(found) if found else None


def _remember(asked: str, found: tuple) -> None:
    remembered = _cache()
    remembered.pop(asked, None)  # so replaying something moves it back to the end
    remembered[asked] = list(found)
    for stale in list(remembered)[:-_CACHE_LIMIT]:
        del remembered[stale]
    _write_cache()


def _forget(asked: str) -> None:
    """Drop a link that did not play, so it gets looked up fresh next time."""
    if _cache().pop(asked, None) is not None:
        _write_cache()


def _write_cache() -> None:
    _cache_file().write_text(json.dumps(_remembered), encoding="utf-8")


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
    "acoustic", "edit", "version", "demo", "tribute", "deluxe",
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
    # some results run two songs together with an ellipsis, and the whole lot
    # gets read out - worse now that a title is kept rather than found again
    title = re.split(r"\s*\.\.\.", title)[0]
    title = re.sub(r"\s*-\s*song and lyrics by\s*", " by ", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*-\s*songs? by\s*", " by ", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*-\s*albums? by\s*", " by ", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*-\s*playlist by\s*", " by ", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*[-|]\s*Spotify\s*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip(" -")
    return title[:80]
