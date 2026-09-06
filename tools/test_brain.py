"""Check the model answers sensibly, and looks things up when it should.

Each question runs several times, because the failure that mattered was not
"wrong once" but "different every time".
"""

import time

from gab import brain

RUNS = 3

# (question, expected route)
QUESTIONS = [
    ("What is the boiling point of water in Fahrenheit?", "direct"),
    ("Explain what a MOSFET does.", "direct"),
    ("What is 18 times four?", "direct"),
    ("How long does it take to drive from Denver to Salt Lake City?", "search"),
    ("Who won the most recent Super Bowl?", "search"),
    ("What is the weather in Bozeman Montana today?", "weather"),
    ("Is it cold outside in Denver?", "weather"),
]

print("starting the model server...")
started = time.perf_counter()
brain.start()
print(f"ready in {time.perf_counter() - started:.1f}s\n")

score = 0
total = 0

for question, expected in QUESTIONS:
    print(f"Q: {question}   (expect: {expected})")
    for _ in range(RUNS):
        looked_up = []
        asked = time.perf_counter()
        reply = brain.answer(question, on_searching=looked_up.append)
        elapsed = time.perf_counter() - asked

        if not looked_up:
            route = "direct"
        elif looked_up[0].startswith("weather in "):
            route = "weather"
        else:
            route = "search"

        correct = route == expected
        score += correct
        total += 1
        print(f"   [{'ok ' if correct else 'BAD'}] {elapsed:5.2f}s {route:<7} {reply[:92]}")
    print()

print(f"routed correctly on {score} of {total} runs")
brain.stop()
