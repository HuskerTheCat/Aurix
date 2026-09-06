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

Working end to end. Say the wake word, ask a question, hear the answer.

| Piece | Status |
|---|---|
| Microphone capture with automatic stop | working |
| Speech to text | working |
| Tray icon and on-screen orb | working |
| Answering questions | working |
| Web search and weather | working |
| Spoken replies | working |
| Wake word | working, using a stand-in until "Hey Gab" is trained |
| Installer | not started |

Known rough edges:

- The voice is a placeholder nobody is fond of. Kokoro is the likely upgrade.
- Deciding you have stopped talking is a fixed one-second timer. Proper
  voice-activity detection would be both safer and faster.
- The room is measured once at startup, so a noise at the wrong moment sets a
  bad threshold for the whole session.
- Nothing interrupts an answer part way through.

## Running it

Requires Python 3.10 or newer.

```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

The language model and the voice live in `runtime/`, which is not in this
repository because of its size. The first run also downloads the speech model
(about 150 MB). After that it works offline.

Say the wake word, or press **Ctrl+Alt+G**, then ask your question.
Quit from the tray icon.

## How it works

1. A small model listens constantly for the wake word. It transcribes nothing
   and keeps nothing, and costs about a third of one percent of a processor.
2. Once woken, it records your question and stops when you stop talking.
3. Speech becomes text, on the processor, in about half a second.
4. One short question decides whether the answer needs looking up. Asking this
   separately is what makes it reliable - asked as part of answering, a small
   model announces it will search and then does not.
5. If needed, it searches the web or fetches the weather, then answers from
   what it found.
6. The answer is read aloud.

Nothing leaves your machine except a search query, and only when a question
needs one.

## Built with

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - speech recognition
- [openWakeWord](https://github.com/dscripka/openWakeWord) - wake word detection
- [llama.cpp](https://github.com/ggml-org/llama.cpp) - the language model
- [Piper](https://github.com/rhasspy/piper) - the voice
