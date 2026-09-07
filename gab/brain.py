"""The local language model, and deciding when to look something up.

Runs llama.cpp's server as a child process and talks to it over HTTP on this
machine only. Answering is two steps: a one-line routing question, then the
answer itself. Asked together, a 4B model volunteers a search only about half
the time.
"""

import datetime
import json
import re
import subprocess
import time

import httpx

from . import catalog, config, paths, search

_process: subprocess.Popen | None = None
_client: httpx.Client | None = None
_hardware: dict = {}
_last_answer: dict = {}

_THINKING = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)

# What the model server says about the machine, at -lv 4.
_ACCELERATOR = r"(?:Vulkan|CUDA|ROCm|Metal|SYCL)\d+"
_DEVICE = re.compile(rf"- {_ACCELERATOR} : (.+?) \((\d+) MiB")
_LAYERS = re.compile(r"offloaded (\d+)/(\d+) layers to GPU")
_VRAM = re.compile(rf"{_ACCELERATOR} model buffer size =\s+([\d.]+) MiB")


def _base_url() -> str:
    return f"http://127.0.0.1:{config.LLAMA_PORT}"


def _today() -> str:
    return datetime.datetime.now().strftime("%A, %d %B %Y")


def start() -> None:
    """Launch the model server and wait until it is ready to answer."""
    global _process, _client, _hardware

    server = paths.resolve(config.LLAMA_SERVER)
    model = catalog.model_file(catalog.chosen_model())
    if not server.exists():
        raise FileNotFoundError(f"llama server missing: {server}")
    if not model.exists():
        raise FileNotFoundError(f"model missing: {model}")

    _hardware = {}

    _process = subprocess.Popen(
        [
            str(server),
            "--model", str(model),
            "--port", str(config.LLAMA_PORT),
            "--host", "127.0.0.1",
            "--ctx-size", str(config.CONTEXT_SIZE),
            "--n-gpu-layers", str(config.GPU_LAYERS),
            # Qwen rambles to itself forever without this and never answers
            "--reasoning", "off",
            "--no-webui",
            # 4 is the level that names the graphics card without logging every token
            "-lv", "4",
            "--log-colors", "off",
            "--log-file", str(paths.llama_log()),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    _client = httpx.Client(timeout=httpx.Timeout(120.0, connect=5.0))
    _wait_until_ready()
    _hardware = _read_hardware()


def _read_hardware() -> dict:
    """Pull what the server said about the machine out of its own log.

    This is the only honest answer to "is it actually on the graphics card" -
    llama.cpp falls back to the processor without complaining.
    """
    log = paths.llama_log()
    if not log.exists():
        return {}

    text = log.read_text(encoding="utf-8", errors="replace")
    found = {}

    device = _DEVICE.findall(text)
    if device:
        found["device"] = device[0][0].strip()
        found["card_mb"] = int(device[0][1])

    layers = _LAYERS.findall(text)
    if layers:
        found["layers"] = int(layers[-1][0])
        found["of_layers"] = int(layers[-1][1])

    vram = _VRAM.findall(text)
    if vram:
        found["vram_mb"] = max(float(value) for value in vram)

    return found


def hardware() -> dict:
    """What the model server reported about the graphics card."""
    return dict(_hardware)


def last_answer() -> dict:
    """Words and seconds from the most recent answer."""
    return dict(_last_answer)


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


def _ask(messages: list, max_tokens: int, temperature: float, on_token=None) -> str:
    """Send an exchange to the model and stream the reply back."""
    request = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
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
            piece = (json.loads(payload)["choices"][0].get("delta") or {}).get("content")
            if not piece:
                continue
            pieces.append(piece)
            if on_token is not None:
                on_token(piece)

    return _THINKING.sub("", "".join(pieces)).strip()


def _route(question: str) -> tuple[str, str]:
    """Decide how to answer. Returns ('direct'|'search'|'weather', argument)."""
    prompt = config.DECISION_PROMPT.format(today=_today(), question=question)
    verdict = _ask(
        [{"role": "user", "content": prompt}],
        max_tokens=config.SEARCH_DECISION_TOKENS,
        temperature=0.0,
    )

    line = verdict.strip().splitlines()[0].strip() if verdict.strip() else ""
    upper = line.upper()

    if upper.startswith("WEATHER:"):
        return "weather", line[len("WEATHER:") :].strip().strip('"')
    if upper.startswith("SEARCH:"):
        return "search", line[len("SEARCH:") :].strip().strip('"') or question
    return "direct", ""


def answer(question: str, on_token=None, on_searching=None) -> str:
    """Answer a question, looking it up first when the answer depends on it.

    on_token is called with each new piece of the spoken answer.
    on_searching is called with what is being looked up, so the orb can say so.
    """
    global _last_answer
    if _client is None:
        raise RuntimeError("brain.start() must be called before answer()")

    route, argument = _route(question)

    content = question
    if route == "weather":
        if on_searching is not None:
            on_searching(f"weather in {argument}")
        content = f"{search.weather(argument)}\n\nQuestion: {question}"
    elif route == "search":
        if on_searching is not None:
            on_searching(argument)
        content = f"Search results:\n\n{search.web_search(argument)}\n\nQuestion: {question}"

    started = time.perf_counter()
    reply = _ask(
        [
            {"role": "system", "content": config.SYSTEM_PROMPT.format(today=_today())},
            {"role": "user", "content": content},
        ],
        max_tokens=config.MAX_ANSWER_TOKENS,
        temperature=config.TEMPERATURE,
        on_token=on_token,
    )

    seconds = time.perf_counter() - started
    _last_answer = {"words": len(reply.split()), "seconds": seconds, "looked_up": route}
    return reply


def restart() -> None:
    """Swap to whichever model is chosen now. Takes a while on a big one."""
    stop()
    start()


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
