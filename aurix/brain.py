"""The local language model, and deciding when to look something up.

Runs llama.cpp's server as a child process and talks to it over HTTP on this
machine only. Answering is two steps: a one-line routing question, then the
answer itself. Asked together, a 4B model volunteers a search only about half
the time.
"""

import ctypes
import datetime
import json
import re
import socket
import subprocess
import time

import httpx

from . import (
    actions, catalog, config, memory, paths, programs, search, settings, spotify,
)

_process: subprocess.Popen | None = None
_client: httpx.Client | None = None
_hardware: dict = {}
_last_answer: dict = {}
_history: list[tuple[str, str]] = []  # what has been asked and answered
_on_card = True  # False while gaming mode has it running on the processor
_spoke_at: float = 0.0

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

    # Without this it would happily talk to somebody else's model server and
    # look like it was working, which is how two copies ended up answering.
    if _port_in_use():
        raise RuntimeError(
            f"port {config.LLAMA_PORT} is already taken, so another copy is "
            "still running. Close it and try again."
        )

    _hardware = {}

    _process = subprocess.Popen(
        [
            str(server),
            "--model", str(model),
            "--port", str(config.LLAMA_PORT),
            "--host", "127.0.0.1",
            "--ctx-size", str(config.CONTEXT_SIZE),
            # 0 puts the whole thing on the processor, which is what
            # gaming mode does to keep off a card something else is using
            "--n-gpu-layers", str(config.GPU_LAYERS if _on_card else 0),
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


def _port_in_use() -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(("127.0.0.1", config.LLAMA_PORT)) == 0


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


class _MemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def memory_mb() -> float | None:
    """What the model server is using right now, rather than when it loaded.

    The startup numbers come out of its log and never move. This is the live
    figure, which is the one worth seeing while it is busy answering.
    """
    if _process is None:
        return None

    query_limited_information = 0x1000
    vm_read = 0x0010
    handle = ctypes.windll.kernel32.OpenProcess(
        query_limited_information | vm_read, False, _process.pid
    )
    if not handle:
        return None
    try:
        counters = _MemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        if not ctypes.windll.psapi.GetProcessMemoryInfo(
            handle, ctypes.byref(counters), counters.cb
        ):
            return None
        return counters.WorkingSetSize / 1024 / 1024
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


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


def forget() -> None:
    """Drop the conversation so far."""
    _history.clear()


def _drop_stale() -> None:
    """A question minutes after the last one is a new conversation, not a follow-up."""
    if _history and time.monotonic() - _spoke_at > config.MEMORY_TIMEOUT_SEC:
        forget()


def _route(question: str) -> tuple[str, str]:
    """Decide how to answer. Returns ('direct'|'search'|'weather', argument)."""
    recent = ""
    if _history:
        # every question, because the subject is often several turns back
        recent = config.RECENT_PROMPT.format(
            questions="; ".join(f'"{asked}"' for asked, _ in _history),
            answer=_history[-1][1],
        )

    prompt = config.DECISION_PROMPT.format(
        today=_today(), question=question, recent=recent
    )
    verdict = _ask(
        [{"role": "user", "content": prompt}],
        max_tokens=config.SEARCH_DECISION_TOKENS,
        temperature=0.0,
    )

    line = verdict.strip().splitlines()[0].strip() if verdict.strip() else ""
    upper = line.upper()

    for verb in (
        "PLAY", "QUEUE", "CONTROL", "VOLUME", "OPEN", "LAUNCH", "TIME", "WEATHER",
        "SEARCH",
    ):
        if upper.startswith(f"{verb}:"):
            argument = line[len(verb) + 1 :].strip().strip('"')
            if verb == "SEARCH":
                return "search", argument or question
            if not argument:
                break  # a doing verb with nothing to do is not a decision
            return verb.lower(), argument
    return "direct", ""


# Handled without asking the model anything, so they are as quick as the thing
# itself. The flag is whether something gets looked up first, which the orb says.
_DOING = {
    "play": (spotify.play, True),
    "queue": (spotify.queue, True),
    "control": (actions.control, False),
    "volume": (actions.volume, False),
    "open": (actions.open_page, False),
    "launch": (programs.launch, False),
    # straight off the clock - asked through the model it used to claim it had
    # no way of knowing, or answer from the weather, which has no time in it
    "time": (search.local_time, False),
}


def _do(route, argument, question, on_token, on_searching) -> str:
    """Carry out a request instead of answering it.

    No model call, so this is as quick as whatever it is being asked to do.
    """
    global _last_answer, _spoke_at
    doing, looks_up = _DOING[route]

    if looks_up and on_searching is not None:
        on_searching(argument)

    started = time.perf_counter()
    try:
        said = doing(argument)
    except Exception as error:  # noqa: BLE001 - say so rather than falling over
        print(f"  could not {route} {argument!r}: {error!r}")
        said = "I could not do that."

    if on_token is not None:
        on_token(said)

    _history.append((question, said))
    del _history[: -config.MEMORY_TURNS]
    _spoke_at = time.monotonic()
    _last_answer = {
        "words": len(said.split()),
        "seconds": time.perf_counter() - started,
        "looked_up": route,
    }
    return said


def _fun() -> bool:
    return settings.get("fun_mode")


def _style() -> str:
    """The one part of the prompt that changes with the mode."""
    return config.FUN_STYLE if _fun() else config.FAST_STYLE


def _looseness() -> float:
    """Character comes as much from a looser temperature as from the wording."""
    return config.FUN_TEMPERATURE if _fun() else config.TEMPERATURE


def _room_to_talk() -> int:
    return config.FUN_MAX_ANSWER_TOKENS if _fun() else config.MAX_ANSWER_TOKENS


def _consider_remembering(question: str, reply: str) -> None:
    """Decide whether the exchange said anything about them worth keeping.

    Called once the answer is written and already being spoken, so the model
    call costs nothing anybody waits for. It can fail - a note not written is
    not worth losing the answer over, and the log says when it happens.
    """
    verdict = _ask(
        [{
            "role": "user",
            "content": config.REMEMBER_PROMPT.format(question=question, answer=reply),
        }],
        max_tokens=config.REMEMBER_TOKENS,
        temperature=0.0,
    )

    line = verdict.strip().splitlines()[0].strip() if verdict.strip() else ""
    if not line.upper().startswith("REMEMBER:"):
        return

    fact = line[len("REMEMBER:") :].strip().strip('"')
    if not fact:
        return
    memory.remember(fact)
    print(f"  remembered: {fact}")


def answer(question: str, on_token=None, on_searching=None) -> str:
    """Answer a question, looking it up first when the answer depends on it.

    on_token is called with each new piece of the spoken answer.
    on_searching is called with what is being looked up, so the orb can say so.
    """
    global _last_answer, _spoke_at
    if _client is None:
        raise RuntimeError("brain.start() must be called before answer()")

    _drop_stale()
    route, argument = _route(question)
    print(f"  route: {route} {argument}".rstrip())

    if route in _DOING:
        return _do(route, argument, question, on_token, on_searching)

    content = question
    if route == "weather":
        if on_searching is not None:
            on_searching(f"weather in {argument}")
        content = f"{search.weather(argument)}\n\nQuestion: {question}"
    elif route == "search":
        if on_searching is not None:
            on_searching(argument)
        content = f"Search results:\n\n{search.web_search(argument)}\n\nQuestion: {question}"

    messages = [
        {
            "role": "system",
            "content": config.SYSTEM_PROMPT.format(
                today=_today(), creator=config.CREATOR, style=_style(),
                memory=memory.for_prompt(),
            ),
        }
    ]
    for asked, replied in _history:
        messages.append({"role": "user", "content": asked})
        messages.append({"role": "assistant", "content": replied})
    messages.append({"role": "user", "content": content})

    started = time.perf_counter()
    reply = _ask(
        messages,
        max_tokens=_room_to_talk(),
        temperature=_looseness(),
        on_token=on_token,
    )

    # the bare question is remembered, not the search results it was wrapped in
    _history.append((question, reply))
    del _history[: -config.MEMORY_TURNS]
    _spoke_at = time.monotonic()

    seconds = time.perf_counter() - started
    _last_answer = {"words": len(reply.split()), "seconds": seconds, "looked_up": route}

    try:
        _consider_remembering(question, reply)
    except Exception as error:  # noqa: BLE001 - never lose an answer over a note
        print(f"  could not decide what to remember: {error!r}")

    return reply


def on_the_card() -> bool:
    """Whether the model is running on the graphics card right now."""
    return _on_card


def use_the_card(wanted: bool) -> None:
    """Move the model onto the card or off it. Restarts the server.

    Does nothing when it is already where it should be, because the restart is
    the expensive part - about two seconds for the 4B.
    """
    global _on_card
    if wanted == _on_card:
        return
    _on_card = wanted
    print(f"  moving the model {'onto the card' if wanted else 'off the card'}")
    restart()


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
