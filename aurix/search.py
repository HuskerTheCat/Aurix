"""Web search, weather and the time. None of it needs an account or a key.

Everything that goes out is noted here, so the settings window can show the last
one. The claim is that nothing but a search query ever leaves this machine, and
being able to read the query back is what makes that checkable rather than
something you have to take on trust.
"""

import datetime
import time

import httpx
from ddgs import DDGS

from . import config

_last_lookup: tuple[str, float] | None = None


def note_lookup(query: str) -> None:
    """Remember something that just left this machine."""
    global _last_lookup
    _last_lookup = (query, time.time())


def last_lookup():
    """The last thing sent off this machine and when, or None if nothing has."""
    return _last_lookup


def weather(place: str) -> str:
    """Current conditions and today's forecast, as plain text for the model."""
    note_lookup(f"weather in {place}")
    reply = httpx.get(
        f"https://wttr.in/{place}",
        params={"format": "j1"},
        headers={"User-Agent": "curl/8"},
        timeout=config.WEATHER_TIMEOUT_SEC,
    )
    reply.raise_for_status()
    data = reply.json()

    now = data["current_condition"][0]
    today = data["weather"][0]
    return (
        f"Weather for {place} right now: {now['temp_F']} degrees Fahrenheit, "
        f"{now['weatherDesc'][0]['value'].strip().lower()}, "
        f"feels like {now['FeelsLikeF']}, humidity {now['humidity']} percent, "
        f"wind {now['windspeedMiles']} miles per hour.\n"
        f"Today: high {today['maxtempF']}, low {today['mintempF']}."
    )


def local_time(place: str) -> str:
    """What time it is somewhere, spoken. Same service as the weather.

    Answered straight from the clock rather than through the model, which used
    to insist it had no way of knowing.
    """
    if place.strip().lower() in ("here", "", "local", "my location"):
        now = datetime.datetime.now()
        return f"It is {_spoken_clock(now.hour, now.minute)}."

    note_lookup(f"time in {place}")
    reply = httpx.get(
        f"https://wttr.in/{place}",
        params={"format": "%T %Z"},
        headers={"User-Agent": "curl/8"},
        timeout=config.WEATHER_TIMEOUT_SEC,
    )
    reply.raise_for_status()

    clock = reply.text.strip().split(" ")[0]
    if ":" not in clock:
        return f"I could not find the time in {place}."

    hours, minutes = (int(part) for part in clock.split(":")[:2])
    return f"It is {_spoken_clock(hours, minutes)} in {place}."


def _spoken_clock(hours: int, minutes: int) -> str:
    part_of_day = (
        "in the morning" if hours < 12
        else "in the afternoon" if hours < 18
        else "in the evening" if hours < 22
        else "at night"
    )
    return f"{hours % 12 or 12}:{minutes:02d} {part_of_day}"


def web_search(query: str) -> str:
    """Search the web and return the results as plain text for the model to read."""
    note_lookup(query)
    results = list(DDGS().text(query, max_results=config.SEARCH_RESULTS))
    if not results:
        return "No results found."

    blocks = []
    for position, result in enumerate(results, start=1):
        title = (result.get("title") or "").strip()
        body = (result.get("body") or "").strip()[: config.SEARCH_SNIPPET_CHARS]
        blocks.append(f"{position}. {title}\n{body}")
    return "\n\n".join(blocks)
