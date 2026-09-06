"""Check the language model answers sensibly and quickly, before wiring it in."""

import time

from gab import brain

QUESTIONS = [
    "What is the boiling point of water in Fahrenheit?",
    "How long does it take to drive from Denver to Salt Lake City?",
    "Explain what a MOSFET does.",
    "What year is it?",
]

print("starting the model server...")
started = time.perf_counter()
brain.start()
print(f"ready in {time.perf_counter() - started:.1f}s\n")

for question in QUESTIONS:
    first = None
    asked = time.perf_counter()

    def mark(_piece, asked=asked):
        global first
        if first is None:
            first = time.perf_counter() - asked

    reply = brain.answer(question, on_token=mark)
    total = time.perf_counter() - asked
    words = len(reply.split())

    print(f"Q: {question}")
    print(f"A: {reply!r}")
    first_text = f"{first:.2f}s" if first is not None else "never"
    print(
        f"   first word {first_text} | whole answer {total:.2f}s"
        f" | {words} words | {words / total:.1f} words/sec\n"
    )

brain.stop()
print("done")
