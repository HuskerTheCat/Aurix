# Gab

A voice assistant for Windows that runs entirely on your own computer.

Say a wake word, ask a question, get a spoken answer. No account, no API key,
no internet required for the assistant itself.

## Goals

- **Local.** The speech recognition, the answers and the voice all run on your machine.
- **Runs anywhere.** Works on AMD, Intel and NVIDIA graphics, and on plain CPU.
- **One installer.** Download, install, talk. Nothing else to set up.
- **Private.** Nothing is sent anywhere unless it needs a web search to answer.

## Status

Early. Step one is building the audio path: press a hotkey, speak, and see what
it heard. The wake word, the answers, the voice and the on-screen orb all get
built on top of that once it works reliably.

| Piece | Status |
|---|---|
| Microphone capture with automatic stop | working |
| Speech to text | working |
| Tray icon | working |
| "Hey Gab" wake word | not started |
| Answering questions | not started |
| Spoken replies | not started |
| Web search for current information | not started |
| On-screen orb | not started |
| Installer | not started |

## Running it

Requires Python 3.10 or newer.

```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

The first run downloads the speech model (about 150 MB). After that it works offline.

Press **Ctrl+Alt+G**, speak, and the transcription appears in the console.
Quit from the tray icon.

## How it will work

1. A small model listens constantly for the wake word, using almost no CPU.
2. Once woken, it records your question and stops when you stop talking.
3. Speech becomes text.
4. A local language model answers, searching the web first if the question needs
   current information.
5. The answer is spoken back while it is still being written, so there is no
   long pause before you hear anything.

## Built with

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - speech recognition
- [openWakeWord](https://github.com/dscripka/openWakeWord) - wake word detection
- [llama.cpp](https://github.com/ggml-org/llama.cpp) - the language model
- [Piper](https://github.com/rhasspy/piper) - the voice
