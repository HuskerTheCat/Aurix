"""Gab - say the wake word, ask a question, hear the answer.

Qt owns the main thread, because the orb has to be painted there. The tray
icon, the loading and the listening each run on their own thread and only ever
touch the orb by sending a signal, which Qt delivers back on the main thread.

Loading happens on a thread rather than before the window appears, so the tray
icon and the orb show up straight away. Half a minute of nothing on screen
reads as a failed start, and someone who thinks it failed launches a second
copy - which is how you end up with two assistants answering at once.
"""

import ctypes
import sys
import threading
import time

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from pynput import keyboard

from gab import audio, brain, config, paths, settings, speech, tray, voice, wake
from gab.audio import NoSpeechDetected, record_until_silence
from gab.overlay import Overlay
from gab.panel import Panel


class Signals(QObject):
    """The only way a worker thread is allowed to reach the orb."""

    starting = Signal()
    ready = Signal(str)
    listening = Signal()
    level = Signal(float)
    thinking = Signal(str)
    searching = Signal(str)
    answer_started = Signal()
    answer_piece = Signal(str)
    answer_done = Signal()
    failed = Signal(str)
    open_panel = Signal()
    quit = Signal()


signals = Signals()
_busy = threading.Lock()
_listener: wake.Listener | None = None
_hotkeys: keyboard.GlobalHotKeys | None = None
_paused_by_user = False  # the panel's pause switch, kept apart from the automatic one
_instance_lock = None  # held for the life of the process; see _claim_single_instance


# --- making sure only one Gab runs ---


def _claim_single_instance() -> bool:
    """Take a system-wide lock, so a second Gab cannot start.

    Windows releases it when the process ends, a crash included, so it can
    never be left held by a copy that is no longer running.
    """
    global _instance_lock
    already_exists = 183  # ERROR_ALREADY_EXISTS

    kernel32 = ctypes.windll.kernel32
    _instance_lock = kernel32.CreateMutexW(None, False, "Gab-single-instance-7e4c1a96")
    return kernel32.GetLastError() != already_exists


def _say_already_running() -> None:
    """A second launch should explain itself rather than silently do nothing."""
    ctypes.windll.user32.MessageBoxW(
        None,
        "Gab is already running.\n\n"
        "Look for the blue dot in your system tray, next to the clock. "
        "It may be hidden behind the arrow.",
        "Gab",
        0x40,  # an information icon
    )


# --- answering a question ---


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

        print(f'  said:  "{reply}"')
        voice.speak(reply)
        spoken = time.perf_counter()

        # Only now start the fade, so the orb stays up while it is talking.
        signals.answer_done.emit()
        print(
            f"  listen {recorded - started:.1f}s"
            f"  |  transcribe {transcribed - recorded:.2f}s"
            f"  |  answer {finished - transcribed:.2f}s"
            f"  |  speaking {spoken - finished:.2f}s"
        )
    except Exception as error:  # noqa: BLE001 - surface it on screen, keep running
        print(f"  failed: {error!r}")
        signals.failed.emit("Something went wrong")
    finally:
        _busy.release()
        # Listen for the wake word again, but only now - listening any earlier
        # means Gab hears its own voice and wakes itself up. Unless the person
        # switched listening off while Gab was busy, which wins.
        if _listener is not None and not _paused_by_user:
            _listener.resume()


def _trigger() -> None:
    """Start a request, off whichever thread noticed - a key or the wake word."""
    if _listener is not None:
        _listener.pause()
    threading.Thread(target=_handle_request, daemon=True).start()


# --- starting up ---


def _load_everything() -> None:
    """The slow part, on its own thread so the orb can say what is happening."""
    global _listener, _hotkeys

    print("Loading the speech model...")
    speech.load()

    print("Loading the voice...")
    voice.load()

    print("Starting the language model...")
    started = time.perf_counter()
    brain.start()
    print(f"  ready in {time.perf_counter() - started:.1f}s")

    print("Measuring the room, stay quiet for a moment...")
    print(f"Speech threshold set to {audio.calibrate():.5f}")

    _listener = wake.Listener(on_wake=_trigger)
    _listener.start()

    _hotkeys = keyboard.GlobalHotKeys({config.HOTKEY: _trigger})
    _hotkeys.start()

    print(f'Ready. Say "{config.WAKE_WORD_NAME}", or press {config.HOTKEY}.')
    signals.ready.emit(config.WAKE_WORD_NAME)


def main() -> None:
    # The instance check comes before the logging, because starting the log
    # truncates it - a second launch would otherwise wipe the running copy's
    # log, which is the one file worth having when something goes wrong.
    if not _claim_single_instance():
        _say_already_running()
        return

    _start_logging()
    settings.load()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    overlay = Overlay()
    signals.starting.connect(overlay.show_starting)
    signals.ready.connect(overlay.show_ready)
    signals.listening.connect(overlay.begin_listening)
    signals.level.connect(overlay.set_level)
    signals.thinking.connect(overlay.begin_thinking)
    signals.searching.connect(overlay.begin_searching)
    signals.answer_started.connect(overlay.begin_answer)
    signals.answer_piece.connect(overlay.append_answer)
    signals.answer_done.connect(overlay.finish_answer)
    signals.failed.connect(overlay.show_result)
    signals.quit.connect(app.quit)

    def set_paused(paused: bool) -> None:
        """The panel's pause switch. Separate from Gab pausing itself."""
        global _paused_by_user
        _paused_by_user = paused
        if _listener is None:
            return
        _listener.pause() if paused else _listener.resume()

    def quit_gab(icon=None) -> None:
        if _hotkeys is not None:
            _hotkeys.stop()
        if icon is not None:
            icon.stop()
        if _listener is not None:
            _listener.stop()
        voice.stop()
        brain.stop()
        signals.quit.emit()

    panel = Panel(
        on_pause=set_paused,
        on_stop_speaking=voice.stop,
        on_quit=lambda: quit_gab(icon),
    )
    signals.open_panel.connect(panel.toggle)

    icon = tray.create(on_open=signals.open_panel.emit, on_quit=quit_gab)
    threading.Thread(target=icon.run, daemon=True).start()

    # Say something before the slow part starts, not after it finishes.
    overlay.show_starting()
    threading.Thread(target=_load_everything, daemon=True).start()

    try:
        sys.exit(app.exec())
    finally:
        brain.stop()


def _start_logging() -> None:
    """Packaged, there is no console, so send everything printed to a file."""
    if not getattr(sys, "frozen", False):
        return
    stream = open(paths.log_file(), "w", encoding="utf-8", buffering=1)
    sys.stdout = stream
    sys.stderr = stream


if __name__ == "__main__":
    main()
