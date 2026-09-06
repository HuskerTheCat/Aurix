"""Check that keyless web search actually returns useful text."""

import time

from ddgs import DDGS

QUERIES = [
    "driving time Denver to Salt Lake City hours",
    "weather Bozeman Montana today",
    "who won the most recent Super Bowl",
]

for query in QUERIES:
    started = time.perf_counter()
    try:
        results = list(DDGS().text(query, max_results=3))
    except Exception as error:
        print(f"{query}\n  FAILED: {error!r}\n")
        continue

    print(f"{query}   ({time.perf_counter() - started:.2f}s, {len(results)} results)")
    for r in results:
        print(f"  - {r.get('title', '')[:70]}")
        print(f"    {r.get('body', '')[:200]}")
    print()
