"""Doing things on the computer: opening pages, and the media keys.

The only two things Aurix will ever launch are a web link and Spotify. It never
runs a program the model names, so a misheard sentence cannot start anything.
Music itself lives in spotify.py.
"""

import re
import webbrowser
from urllib.parse import quote_plus

from ddgs import DDGS
from . import keys, spotify

_WEB_ADDRESS = re.compile(r"\b((?:https?://)?[\w-]+(?:\.[\w-]+)+(?:/\S*)?)")

# Sites worth going to directly rather than through a search engine.
SITES = {
    "youtube": ("https://www.youtube.com", "https://www.youtube.com/results?search_query={q}"),
    "wikipedia": ("https://en.wikipedia.org", "https://en.wikipedia.org/w/index.php?search={q}"),
    "github": ("https://github.com", "https://github.com/search?q={q}"),
    "reddit": ("https://www.reddit.com", "https://www.reddit.com/search/?q={q}"),
    "twitch": ("https://www.twitch.tv", "https://www.twitch.tv/search?term={q}"),
    "amazon": ("https://www.amazon.com", "https://www.amazon.com/s?k={q}"),
    "google": ("https://www.google.com", "https://www.google.com/search?q={q}"),
    "maps": ("https://www.google.com/maps", "https://www.google.com/maps/search/{q}"),
}

# Words that carry no meaning once the site has been picked out.
_FILLER = {
    "page", "pages", "for", "the", "a", "an", "of", "on", "about", "video",
    "videos", "search", "up", "pull", "open", "website", "site", "results",
    "me", "please", "to", "and", "some",
}

# Windows moves the volume two percent per key press.
_VOLUME_STEP = 2
_NUDGE = 5  # presses for "turn it up", so about ten percent
_TO_SILENCE = 51  # presses to reach zero from anywhere


# --- music ---


def control(command: str) -> str:
    """Pause, resume, skip, go back or start the song again."""
    command = command.strip().lower()
    playing, track = spotify.state()

    if command == "pause":
        # Only Spotify's state is knowable, so when it is shut the key still
        # goes out and whatever else is playing gets it.
        if playing == "playing" or playing == "closed":
            keys.tap(keys.PLAY_PAUSE)
            return "Paused."
        return "Nothing is playing."

    if command == "resume":
        if playing == "playing":
            return f"Already playing {track}."
        keys.tap(keys.PLAY_PAUSE)
        return "Playing."

    if command == "next":
        return spotify.skip()

    if command == "back":
        # One press restarts the song, so going back a track takes two.
        keys.tap(keys.PREVIOUS, 2)
        return "Going back."

    if command == "restart":
        keys.tap(keys.PREVIOUS)
        return "From the top."

    raise ValueError(f"unknown music command {command!r}")


def volume(setting: str) -> str:
    """Turn it up, down, mute it, or set it to a number out of a hundred."""
    setting = setting.strip().lower()

    if setting in ("up", "louder"):
        keys.tap(keys.LOUDER, _NUDGE)
        return "Turned it up."
    if setting in ("down", "quieter"):
        keys.tap(keys.QUIETER, _NUDGE)
        return "Turned it down."
    if setting in ("mute", "unmute"):
        keys.tap(keys.MUTE)
        return "Muted." if setting == "mute" else "Unmuted."

    wanted = re.search(r"\d+", setting)
    if wanted is None:
        raise ValueError(f"unknown volume {setting!r}")

    percent = max(0, min(100, int(wanted.group())))
    # There is no key for "set to 40", so drop to silence and climb back.
    keys.tap(keys.QUIETER, _TO_SILENCE)
    keys.tap(keys.LOUDER, percent // _VOLUME_STEP)
    return f"Volume {percent}."


# --- web pages ---


def open_page(request: str) -> str:
    """Open a web page in the usual browser. Returns what to say back."""
    request = request.strip()

    site, rest = _pick_site(request)
    if site is not None:
        home, search = SITES[site]
        if rest:
            _browse(search.format(q=quote_plus(rest)))
            return f"Searching {site} for {rest}."
        _browse(home)
        return f"Opening {site}."

    address = _as_address(request)
    if address is not None:
        _browse(address)
        return f"Opening {_name_of(address)}."

    top = _first_result(request)
    if top is None:
        return f"I could not find a page for {request}."
    _browse(top)
    return f"Opening {_name_of(top)}."


def _browse(url: str) -> None:
    """Open a link. Anything that is not a web address is refused outright."""
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"not a web address: {url!r}")
    webbrowser.open(url)


def _pick_site(request: str):
    """Find a known site in the request, and whatever is being looked for on it."""
    words = re.findall(r"[\w']+", request.lower())
    for position, word in enumerate(words):
        if word in SITES:
            rest = words[position + 1 :]
            while rest and rest[0] in _FILLER:
                rest.pop(0)
            return word, " ".join(rest)
    return None, ""


def _as_address(request: str):
    """Spot an actual web address, so "open bbc.co.uk" goes straight there."""
    match = _WEB_ADDRESS.search(request.replace(" dot ", "."))
    if match is None:
        return None
    found = match.group(1)
    return found if found.startswith("http") else f"https://{found}"


def _name_of(url: str) -> str:
    """The bit of a link worth reading aloud."""
    return url.split("//", 1)[-1].split("/", 1)[0].removeprefix("www.")


def _first_result(query: str):
    for result in DDGS().text(query, max_results=3):
        link = result.get("href") or ""
        if link.startswith(("http://", "https://")):
            return link
    return None
