# Gab

A voice assistant that runs on your own computer. No account, no API key, and
nothing leaves the machine except a web search when a question needs one.

![Gab](docs/orb-done.png)

## Install

Grab the installer from [Releases](../../releases) and run it. It pulls down
the language model during setup, so that's the only step.

Windows will call it unrecognised because it isn't signed - hit **More info**,
then **Run anyway**.

## Using it

Sits in the system tray as a blue dot.

- Say **"Hey Jarvis"**, pause, then ask.
- Or press **Ctrl + Alt + G**.
- Click the tray icon for settings.

![Settings](docs/panel.png)

## Building it

```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

The models live in `runtime/`, which isn't in the repo. To build the installer:

```powershell
.venv\Scripts\pyinstaller --noconfirm gab.spec
"$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer.iss
```

Built on [faster-whisper](https://github.com/SYSTRAN/faster-whisper),
[openWakeWord](https://github.com/dscripka/openWakeWord),
[llama.cpp](https://github.com/ggml-org/llama.cpp) and
[Piper](https://github.com/rhasspy/piper).
