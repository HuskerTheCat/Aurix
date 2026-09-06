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
| Installer | working, 3.2 GB, installs and runs with nothing else needed |

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

The models live in `runtime/`, which is not in this repository because of its
size. Nothing is downloaded at runtime - the speech model, the voice, the
language model and the wake word all ship with the app.

Say the wake word, or press **Ctrl+Alt+G**, then ask your question.
Quit from the tray icon.

## Building the installer

```powershell
.venv\Scripts\pyinstaller --noconfirm gab.spec
"$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer.iss
```

The first step makes `dist\Gab\`, an app that runs without Python. The second
wraps it together with `runtime\` into a single installer, about 3.2 GB, which
takes roughly ten minutes to compress.

`runtime\` is read straight from the project folder rather than copied into
`dist\` first. That is deliberate: the duplicate is three gigabytes and filled
a disk once already.

The installed app needs about 3.6 GB. It offers to start with Windows and to
add a desktop shortcut, and uninstalls cleanly.

An unsigned installer makes Windows show a SmartScreen warning the first time.
That goes away with a code signing certificate, which costs money each year.

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
