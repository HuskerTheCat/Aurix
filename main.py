"""Gab - press the hotkey, ask a question, get an answer.

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

from gab import audio, brain, config, speech, tray
from gab.audio import NoSpeechDetected, record_until_silence
from gab.overlay import Overlay


class Signals(QObject):
    """The only way a worker thread is allowed to reach the orb."""

    listening = Signal()
    level = Signal(float)
    thinking = Signal(str)
    searching = Signal(str)
    answer_started = Signal()
    answer_piece = Signal(str)
    answer_done = Signal()
    failed = Signal(str)
    quit = Signal()


signals = Signals()
_busy = threading.Lock()


def _handle_request() -> None:
    """One full listen, transcribe and answer cycle. Runs on its own thread."""
    if not _busy.acquire(blocking=False):
        return  # already busy, ignore the extra press
    try:
        signals.listening.emit()
        started = time.perf_counter()

        try:
            recording = record_until_silence(on_level=signals.level.emit)
        except NoSpeechDetected as error:
            print(f"  heard nothing - {error}")
            signals.failed.emit("Didn't hear anything")
            return

        recorded = time.perf_counter()
        question = speech.transcribe(recording)
        transcribed = time.perf_counter()

        if not question:
            print("  heard: (nothing recognisable)")
            signals.failed.emit("Didn't catch that")
            return

        print(f'  heard: "{question}"')
        signals.thinking.emit(question)

        first_word_at = None

        def on_piece(piece: str) -> None:
            nonlocal first_word_at
            if first_word_at is None:
                first_word_at = time.perf_counter()
                signals.answer_started.emit()
            signals.answer_piece.emit(piece)

        reply = brain.answer(
            question, on_token=on_piece, on_searching=signals.searching.emit
        )
        finished = time.perf_counter()

        signals.answer_done.emit()
        print(f'  said:  "{reply}"')
        print(
            f"  listen {recorded - started:.1f}s"
            f"  |  transcribe {transcribed - recorded:.2f}s"
            f"  |  first word {(first_word_at or finished) - transcribed:.2f}s"
            f"  |  whole answer {finished - transcribed:.2f}s"
        )
    except Exception as error:  # noqa: BLE001 - surface it on screen, keep running
        print(f"  failed: {error!r}")
        signals.failed.emit("Something went wrong")
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
    signals.searching.connect(overlay.begin_searching)
    signals.answer_started.connect(overlay.begin_answer)
    signals.answer_piece.connect(overlay.append_answer)
    signals.answer_done.connect(overlay.finish_answer)
    signals.failed.connect(overlay.show_result)
    signals.quit.connect(app.quit)

    print("Loading the speech model...")
    speech.load()

    print("Starting the language model...")
    model_started = time.perf_counter()
    brain.start()
    print(f"  ready in {time.perf_counter() - model_started:.1f}s")

    print("Measuring the room, stay quiet for a moment...")
    print(f"Speech threshold set to {audio.calibrate():.5f}")

    hotkeys = keyboard.GlobalHotKeys({config.HOTKEY: _on_hotkey})
    hotkeys.start()

    def quit_gab(icon) -> None:
        hotkeys.stop()
        icon.stop()
        brain.stop()
        signals.quit.emit()

    icon = tray.create(on_quit=quit_gab)
    threading.Thread(target=icon.run, daemon=True).start()

    print(f"Ready. Press {config.HOTKEY} and ask something.")
    print("Quit from the tray icon.")

    try:
        sys.exit(app.exec())
    finally:
        brain.stop()


if __name__ == "__main__":
    main()
