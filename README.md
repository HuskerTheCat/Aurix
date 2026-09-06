# Gab

A voice assistant that runs entirely on your own computer.

Say a wake word, ask a question, get a spoken answer. Nothing is sent anywhere,
there is no account, and there is nothing to sign up for.

![Gab answering a question](docs/orb-done.png)

## Install

Download the installer from [Releases](../../releases) and run it. That is the
whole process - the model it needs is fetched during installation.

Windows will warn that the installer is unrecognised, because it is not
code-signed. Click **More info**, then **Run anyway**.

## Use

Gab sits in the system tray as a small blue dot.

- Say **"Hey Jarvis"**, pause, then ask your question.
- Or press **Ctrl + Alt + G** instead of speaking.
- Click the tray icon for settings.

An orb appears at the top of the screen and changes colour as it works:
blue listening, purple thinking, amber looking something up, green answering.

![The tray panel](docs/panel.png)

## How it works

1. A small model listens for the wake word. It transcribes nothing and stores
   nothing, and uses about a third of one percent of a processor.
2. Once woken, it records until you stop talking.
3. Speech becomes text, in about half a second.
4. A short question decides whether the answer needs looking up.
5. If so it searches the web or fetches the weather, then answers from what it
   found.
6. The answer is read aloud.

Only a search query ever leaves the machine, and only when a question needs
one. Your voice does not.

## Requirements

Windows, 64-bit. It uses whatever graphics card is present - AMD, Intel or
NVIDIA - and works on a plain processor with none.

About 3.6 GB of disk, most of it the language model.

## Build from source

Needs Python 3.10 or newer.

```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

The models live in `runtime/`, which is not in this repository because of its
size. To build the installer:

```powershell
.venv\Scripts\pyinstaller --noconfirm gab.spec
"$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer.iss
```

The first step makes `dist\Gab\`, which runs without Python. The second wraps
it into an installer of about 450 MB. The language model is not included - the
installer downloads it, which keeps the file small enough for a GitHub release.

## Layout

```
gab/            the app
  audio.py      recording, and knowing when you stopped talking
  brain.py      the language model, and deciding when to look something up
  overlay.py    the orb
  panel.py      the tray settings panel
  search.py     web search and weather
  settings.py   settings that survive installation
  speech.py     speech to text
  voice.py      text to speech
  wake.py       always-on wake word listening
tools/          development and diagnostic scripts, not part of the app
main.py         starts everything
gab.spec        how the app is packaged
installer.iss   how the installer is built
```

Run a tool from the project root, for example:

```powershell
.venv\Scripts\python -m tools.test_brain
```

## What is left

See [TODO.md](TODO.md).

## Built with

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - speech recognition
- [openWakeWord](https://github.com/dscripka/openWakeWord) - wake word detection
- [llama.cpp](https://github.com/ggml-org/llama.cpp) - the language model
- [Piper](https://github.com/rhasspy/piper) - the voice
