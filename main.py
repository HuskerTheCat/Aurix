"""Gab - press the hotkey, speak, and watch the orb.

Qt owns the main thread, because the orb has to be painted there. The tray
icon and the listening each run on their own thread and only ever touch the
orb by sending a signal, which Qt delivers back on the main thread.
"""

import sys
import threading
import time

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from pynput import keyboard

from gab import audio, config, speech, tray
from gab.audio import NoSpeechDetected, record_until_silence
from gab.overlay import Overlay


class Signals(QObject):
    """The only way a worker thread is allowed to reach the orb."""

    listening = Signal()
    level = Signal(float)
    thinking = Signal()
    result = Signal(str)
    quit = Signal()


signals = Signals()
_busy = threading.Lock()


def _handle_request() -> None:
    """One full listen-and-transcribe cycle. Runs on its own thread."""
    if not _busy.acquire(blocking=False):
        return  # already listening, ignore the extra press
    try:
        signals.listening.emit()
        started = time.perf_counter()

        try:
            recording = record_until_silence(on_level=signals.level.emit)
        except NoSpeechDetected as error:
            print(f"  heard nothing - {error}")
            signals.result.emit("Didn't hear anything")
            return

        recorded = time.perf_counter()
        signals.thinking.emit()

        text = speech.transcribe(recording)
        finished = time.perf_counter()

        signals.result.emit(text or "Didn't catch that")
        print(f'  heard: "{text}"' if text else "  heard: (nothing recognisable)")
        print(
            f"  {len(recording) / config.SAMPLE_RATE:.1f}s audio"
            f"  |  transcribe {finished - recorded:.2f}s"
            f"  |  total {finished - started:.2f}s"
        )
    finally:
        _busy.release()


def _on_hotkey() -> None:
    """Run the work off the key listener thread so hotkeys stay responsive."""
    threading.Thread(target=_handle_request, daemon=True).start()


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    overlay = Overlay()
    signals.listening.connect(overlay.begin_listening)
    signals.level.connect(overlay.set_level)
    signals.thinking.connect(overlay.begin_thinking)
    signals.result.connect(overlay.show_result)
    signals.quit.connect(app.quit)

    print("Loading the speech model (the first run downloads it)...")
    speech.load()

    print("Measuring the room, stay quiet for a moment...")
    print(f"Speech threshold set to {audio.calibrate():.5f}")

    hotkeys = keyboard.GlobalHotKeys({config.HOTKEY: _on_hotkey})
    hotkeys.start()

    def quit_gab(icon) -> None:
        hotkeys.stop()
        icon.stop()
        signals.quit.emit()

    icon = tray.create(on_quit=quit_gab)
    threading.Thread(target=icon.run, daemon=True).start()

    print(f"Ready. Press {config.HOTKEY} and speak.")
    print("Quit from the tray icon.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
