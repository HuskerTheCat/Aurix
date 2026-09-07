"""Doing things on the computer: opening pages, and driving Spotify.

The only two things Aurix will ever launch are a web link and Spotify. It never
runs a program the model names, so a misheard sentence cannot start anything.

Spotify's own API needs a sign-in and a Premium account, which would break the
promise that you just run the installer. Instead the song is looked up with the
same web search everything else uses, and the resulting spotify:track link is
handed to the desktop app, which plays it.
"""

import os
import re
import webbrowser
from urllib.parse import quote_plus

from ddgs import DDGS
from pynput.keyboard import Controller, Key

_keys = Controller()

_SPOTIFY_ID = r"([A-Za-z0-9]{22})"
_LINKS = {
    "track": re.compile(rf"open\.spotify\.com/(?:intl-[a-z-]+/)?track/{_SPOTIFY_ID}"),
    "playlist": re.compile(rf"open\.spotify\.com/(?:intl-[a-z-]+/)?playlist/{_SPOTIFY_ID}"),
}
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

# Windows only has one play/pause key, so both say the same thing to it. Asking
# to pause when nothing is playing therefore starts it, same as a media remote.
_CONTROLS = {
    "pause": (Key.media_play_pause, "Paused."),
    "resume": (Key.media_play_pause, "Playing."),
    "next": (Key.media_next, "Skipped."),
    "back": (Key.media_previous, "Going back."),
}


def control(command: str) -> str:
    """Pause, resume or skip whatever is playing. Works with any music player."""
    wanted = _CONTROLS.get(command.strip().lower())
    if wanted is None:
        raise ValueError(f"unknown music command {command!r}")

    key, said = wanted
    _keys.press(key)
    _keys.release(key)
    return said


def play(request: str) -> str:
    """Play a song, artist or playlist in Spotify. Returns what to say back."""
    kind = "playlist" if "playlist" in request.lower() else "track"
    name = re.sub(r"\bplaylists?\b", "", request, flags=re.IGNORECASE).strip()

    found = _find_on_spotify(name, kind)
    if found is None:
        return f"I could not find {name} on Spotify."

    identifier, title = found
    os.startfile(f"spotify:{kind}:{identifier}")
    return f"Playing {title}."


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


def _find_on_spotify(name: str, kind: str):
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


def _closeness(wanted: str, title: str) -> int:
    """How well a result matches, so "Fleetwood Mac" is not a song of that name.

    Asking for an artist should play one of theirs. Asking for a song should
    play that song. The only clue is which side of "by" the words landed on.
    """
    wanted = wanted.lower().strip()
    song, _, artist = title.lower().partition(" by ")

    if artist and wanted in artist:
        return 3
    if song.startswith(wanted):
        return 2
    if wanted in song:
        return 1
    return 0


def _tidy(title: str) -> str:
    """Search results describe themselves oddly. Cut it back to song and artist."""
    title = title.split("|")[0]
    title = re.sub(r"\s*-\s*song and lyrics by\s*", " by ", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*-\s*songs? by\s*", " by ", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*-\s*playlist by\s*", " by ", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*[-|]\s*Spotify\s*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip(" -")
    return title[:80]
