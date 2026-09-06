"""Dump exactly what the model server sends back, to see why content is empty."""

import json

import httpx

from gab import brain, config

brain.start()
client = httpx.Client(timeout=60.0)
url = f"http://127.0.0.1:{config.LLAMA_PORT}/v1/chat/completions"

body = {
    "messages": [
        {"role": "system", "content": config.SYSTEM_PROMPT},
        {"role": "user", "content": "What is the boiling point of water in Fahrenheit?"},
    ],
    "max_tokens": 200,
    "stream": False,
}

print("=== non-streaming response ===")
reply = client.post(url, json=body).json()
print(json.dumps(reply, indent=2)[:2500])

print("\n=== first 12 streaming chunks ===")
body["stream"] = True
shown = 0
with client.stream("POST", url, json=body) as response:
    for line in response.iter_lines():
        if line.startswith("data: ") and line[6:] != "[DONE]":
            print(line[:300])
            shown += 1
            if shown >= 12:
                break

brain.stop()
