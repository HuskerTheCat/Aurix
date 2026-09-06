"""The local language model that answers questions.

Runs llama.cpp's server as a child process and talks to it over HTTP on this
machine only. Nothing leaves the computer.

Answers stream back a word at a time, which matters: the voice can start
speaking the first sentence while the rest is still being written, instead of
everyone waiting for the whole thing.
"""

import json
import re
import subprocess
import time
from pathlib import Path

import httpx

from . import config

_process: subprocess.Popen | None = None
_client: httpx.Client | None = None

# Some models narrate their reasoning first. Nobody wants that read aloud.
_THINKING = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)


def _base_url() -> str:
    return f"http://127.0.0.1:{config.LLAMA_PORT}"


def start() -> None:
    """Launch the model server and wait until it is ready to answer."""
    global _process, _client

    server = Path(config.LLAMA_SERVER).resolve()
    model = Path(config.MODEL_PATH).resolve()
    if not server.exists():
        raise FileNotFoundError(f"llama server missing: {server}")
    if not model.exists():
        raise FileNotFoundError(f"model missing: {model}")

    _process = subprocess.Popen(
        [
            str(server),
            "--model", str(model),
            "--port", str(config.LLAMA_PORT),
            "--host", "127.0.0.1",
            "--ctx-size", str(config.CONTEXT_SIZE),
            "--n-gpu-layers", str(config.GPU_LAYERS),
            # Qwen narrates its reasoning by default, which for a voice
            # assistant is pure delay - it spends its whole budget thinking
            # out loud and never reaches the answer.
            "--reasoning", "off",
            "--no-webui",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    _client = httpx.Client(timeout=httpx.Timeout(120.0, connect=5.0))
    _wait_until_ready()


def _wait_until_ready() -> None:
    deadline = time.monotonic() + config.LLAMA_START_TIMEOUT_SEC
    while time.monotonic() < deadline:
        if _process is not None and _process.poll() is not None:
            raise RuntimeError(f"model server died on startup (exit {_process.returncode})")
        try:
            if _client.get(f"{_base_url()}/health", timeout=2.0).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise TimeoutError(f"model server not ready after {config.LLAMA_START_TIMEOUT_SEC}s")


def answer(question: str, on_token=None) -> str:
    """Answer a question. on_token, if given, is called with each new piece."""
    if _client is None:
        raise RuntimeError("brain.start() must be called before answer()")

    request = {
        "messages": [
            {"role": "system", "content": config.SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "max_tokens": config.MAX_ANSWER_TOKENS,
        "temperature": config.TEMPERATURE,
        "stream": True,
    }

    pieces = []
    with _client.stream("POST", f"{_base_url()}/v1/chat/completions", json=request) as reply:
        reply.raise_for_status()
        for line in reply.iter_lines():
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                break
            delta = json.loads(payload)["choices"][0].get("delta", {})
            piece = delta.get("content")
            if not piece:
                continue
            pieces.append(piece)
            if on_token is not None:
                on_token(piece)

    return _THINKING.sub("", "".join(pieces)).strip()


def stop() -> None:
    """Shut the model server down."""
    global _process, _client
    if _client is not None:
        _client.close()
        _client = None
    if _process is not None:
        _process.terminate()
        try:
            _process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _process.kill()
        _process = None
