"""Web search and weather. Neither needs an account or a key."""

import httpx
from ddgs import DDGS

from . import config


def weather(place: str) -> str:
    """Current conditions and today's forecast, as plain text for the model."""
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


def web_search(query: str) -> str:
    """Search the web and return the results as plain text for the model to read."""
    results = list(DDGS().text(query, max_results=config.SEARCH_RESULTS))
    if not results:
        return "No results found."

    blocks = []
    for position, result in enumerate(results, start=1):
        title = (result.get("title") or "").strip()
        body = (result.get("body") or "").strip()[: config.SEARCH_SNIPPET_CHARS]
        blocks.append(f"{position}. {title}\n{body}")
    return "\n\n".join(blocks)
