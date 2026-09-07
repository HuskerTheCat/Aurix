"""Gab - say the wake word, ask a question, hear the answer.

Qt owns the main thread because the orb is painted there. The tray icon, the
loading and the listening each run on their own thread and reach the orb only
by signal.
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
from gab.window import Window


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
_paused_by_user = False
_instance_lock = None  # must stay referenced for the life of the process


def _claim_single_instance() -> bool:
    """Take a system-wide lock so a second Gab cannot start."""
    global _instance_lock
    already_exists = 183  # ERROR_ALREADY_EXISTS

    kernel32 = ctypes.windll.kernel32
    _instance_lock = kernel32.CreateMutexW(None, False, "Gab-single-instance-7e4c1a96")
    return kernel32.GetLastError() != already_exists


def _say_already_running() -> None:
    ctypes.windll.user32.MessageBoxW(
        None,
        "Gab is already running.\n\n"
        "Look for the blue dot in your system tray, next to the clock. "
        "It may be hidden behind the arrow.",
        "Gab",
        0x40,  # an information icon
    )


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

        speech_out = voice.begin()
        if settings.get("think_out_loud"):
            speech_out.say_sound(voice.filler())

        first_word_at = None
        unspoken = ""

        def on_piece(piece: str) -> None:
            nonlocal first_word_at, unspoken
            if first_word_at is None:
                first_word_at = time.perf_counter()
                signals.answer_started.emit()
            signals.answer_piece.emit(piece)

            # hand each finished sentence straight to the voice, so it starts
            # talking while the rest of the answer is still being written
            unspoken += piece
            done, unspoken = voice.whole_sentences(unspoken)
            for sentence in done:
                speech_out.say(sentence)

        reply = brain.answer(
            question, on_token=on_piece, on_searching=signals.searching.emit
        )
        finished = time.perf_counter()

        print(f'  said:  "{reply}"')
        speech_out.say(unspoken)
        speech_out.finish()
        spoken = time.perf_counter()

        signals.answer_done.emit()  # after speaking, so the orb stays up
        talking_from = speech_out.started_at or spoken
        print(
            f"  listen {recorded - started:.1f}s"
            f"  |  transcribe {transcribed - recorded:.2f}s"
            f"  |  quiet {talking_from - transcribed:.2f}s"
            f"  |  talking {spoken - talking_from:.2f}s"
            f"  |  answer written in {finished - transcribed:.2f}s"
        )
    except Exception as error:  # noqa: BLE001 - show it, but keep running
        print(f"  failed: {error!r}")
        signals.failed.emit("Something went wrong")
    finally:
        _busy.release()
        # wait until now or it hears itself talking and wakes up again
        if _listener is not None and not _paused_by_user:
            _listener.resume()


def _trigger() -> None:
    if _listener is not None:
        _listener.pause()
    threading.Thread(target=_handle_request, daemon=True).start()


def _swap_model() -> None:
    """Restart the model server on whichever model is chosen now."""
    if _listener is not None:
        _listener.pause()
    with _busy:
        brain.restart()
    if _listener is not None and not _paused_by_user:
        _listener.resume()


def _load_everything() -> None:
    """The slow part, on a thread so the orb can appear first."""
    global _listener, _hotkeys

    print("Loading the speech model...")
    speech.load()
    speech.warm_up()

    print("Loading the voice...")
    voice.load()
    voice.warm_up()

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
    # do this before logging starts, else a second launch wipes the log
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
        global _paused_by_user
        _paused_by_user = paused
        if _listener is None:
            return
        _listener.pause() if paused else _listener.resume()

    def quit_gab(icon=None) -> None:
        settings_window.close()
        if _hotkeys is not None:
            _hotkeys.stop()
        if icon is not None:
            icon.stop()
        if _listener is not None:
            _listener.stop()
        voice.stop()
        brain.stop()
        signals.quit.emit()

    def restyle() -> None:
        panel.restyle()

    settings_window = Window(apply_model=_swap_model, on_theme=restyle)

    panel = Panel(
        on_pause=set_paused,
        on_stop_speaking=voice.stop,
        on_settings=settings_window.open,
        on_quit=lambda: quit_gab(icon),
    )
    signals.open_panel.connect(panel.toggle)

    icon = tray.create(on_open=signals.open_panel.emit, on_quit=quit_gab)
    threading.Thread(target=icon.run, daemon=True).start()

    overlay.show_starting()
    threading.Thread(target=_load_everything, daemon=True).start()

    try:
        sys.exit(app.exec())
    finally:
        brain.stop()


def _start_logging() -> None:
    """Packaged there is no console, so send printed output to a file."""
    if not getattr(sys, "frozen", False):
        return
    stream = open(paths.log_file(), "w", encoding="utf-8", buffering=1)
    sys.stdout = stream
    sys.stderr = stream


if __name__ == "__main__":
    main()
