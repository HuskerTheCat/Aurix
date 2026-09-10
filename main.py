"""Aurix - say the wake word, ask a question, hear the answer.

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

from aurix import (
    audio, brain, catalog, config, cores, gaming, paths, settings, speech,
    timings, tray, voice, wake,
)
from aurix.audio import NoSpeechDetected, record_until_silence
from aurix.overlay import Overlay
from aurix.panel import Panel
from aurix.window import Window


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
_busy_since: float | None = None  # when the running request started, for spotting a stuck one
_listener: wake.Listener | None = None
_hotkeys: keyboard.GlobalHotKeys | None = None
_paused_by_user = False
_instance_lock = None  # must stay referenced for the life of the process


# Deliberately still says Gab. This string is the app's identity, not its name,
# and every version has to use the same one - when the rename changed it, an
# older installed copy stopped seeing the new one and both ran at once, each
# answering out loud. Never change it again.
_INSTANCE_LOCK_NAME = "Gab-single-instance-7e4c1a96"


def _claim_single_instance() -> bool:
    """Take a system-wide lock so a second copy cannot start."""
    global _instance_lock
    already_exists = 183  # ERROR_ALREADY_EXISTS

    kernel32 = ctypes.windll.kernel32
    _instance_lock = kernel32.CreateMutexW(None, False, _INSTANCE_LOCK_NAME)
    return kernel32.GetLastError() != already_exists


def _say_already_running() -> None:
    ctypes.windll.user32.MessageBoxW(
        None,
        "Aurix is already running.\n\n"
        "Look for the blue dot in your system tray, next to the clock. "
        "It may be hidden behind the arrow.",
        "Aurix",
        0x40,  # an information icon
    )


def _handle_request() -> None:
    """One full listen, transcribe and answer cycle. Runs on its own thread."""
    global _busy_since
    speech_out = None
    if not _busy.acquire(blocking=False):
        # This used to say nothing at all. When a request wedged once, every
        # later wake and every hotkey press landed here and vanished, the wake
        # word stayed paused because only the finally below resumes it, and the
        # log stopped dead at "Ready" - which looks exactly like a broken
        # hotkey. Say how long it has been, so slow and stuck read differently.
        running_for = time.monotonic() - (_busy_since or time.monotonic())
        print(f"  still busy with the last request ({running_for:.0f}s), ignoring this one")

        if running_for > config.STUCK_AFTER_SEC:
            # Nothing can safely interrupt the wedged thread - Python cannot
            # kill one - but it must not take the wake word with it silently.
            print(
                f"  the last request has been going for {running_for:.0f}s, which "
                "is not slow, it is stuck. Restart Aurix."
            )
            signals.failed.emit("Stuck on the last question - restart Aurix")
            if _listener is not None and not _paused_by_user:
                _listener.resume()
        return

    _busy_since = time.monotonic()
    try:
        # paused in here rather than in _trigger, so that pausing and resuming
        # are both inside the lock and cannot get out of step. Pausing outside
        # it meant a trigger that arrived while busy paused the listener and
        # then returned without ever resuming it
        if _listener is not None:
            _listener.pause()

        # nothing else is written until the words come back, and recording and
        # transcribing are both able to hang, so mark the start
        print("  listening...")
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
        if not speech_out.finish(config.SPEAKING_PATIENCE_SEC):
            print(
                f"  gave up waiting to finish speaking after "
                f"{config.SPEAKING_PATIENCE_SEC}s - something is wrong with the voice"
            )
        spoken = time.perf_counter()

        signals.answer_done.emit()  # after speaking, so the orb stays up
        talking_from = speech_out.started_at or spoken
        timings.record(
            listen=recorded - started,
            transcribe=transcribed - recorded,
            quiet=talking_from - transcribed,
            talking=spoken - talking_from,
            written=finished - transcribed,
        )
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
        # it is only finished on the way out of a good answer, so without this
        # a failure part way through left its speaking thread blocked forever
        if speech_out is not None:
            speech_out.cancel()
    finally:
        _busy_since = None
        _busy.release()
        # wait until now or it hears itself talking and wakes up again
        if _listener is not None and not _paused_by_user:
            _listener.resume()


def _trigger() -> None:
    threading.Thread(target=_handle_request, daemon=True).start()


def _watch_the_card() -> None:
    """Keep the model off the graphics card while something else needs it."""
    decision = gaming.Decision()
    while True:
        time.sleep(config.GAMING_POLL_SEC)
        try:
            _consider_the_card(decision)
        except Exception as error:  # noqa: BLE001 - never take the app down over this
            print(f"  could not check the graphics card: {error!r}")


def _consider_the_card(decision: gaming.Decision) -> None:
    choice = gaming.chosen()
    if choice == "off":
        wanted = True  # stay on the card whatever else is running
    elif choice == "on":
        wanted = False  # forced onto the processor
    else:
        settled = decision.update(
            gaming.should_get_off(brain.hardware().get("card_mb"), brain.on_the_card())
        )
        if settled is None:
            return  # not sure yet, or not steady long enough to act on
        wanted = not settled

    if wanted == brain.on_the_card():
        return

    # not in the middle of answering something - it will come round again in
    # ten seconds, and a restart underneath a live question would lose it
    if not _busy.acquire(blocking=False):
        return
    try:
        if _listener is not None:
            _listener.pause()
        brain.use_the_card(wanted)
    finally:
        _busy.release()
        if _listener is not None and not _paused_by_user:
            _listener.resume()


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
    try:
        _load()
    except Exception as error:  # noqa: BLE001 - say so instead of hanging on "Starting"
        print(f"could not start: {error!r}")
        signals.failed.emit(str(error))


def _load() -> None:
    global _listener, _hotkeys

    print("Loading the speech model...")
    speech.load()
    speech.warm_up()

    print("Loading the voice detector...")
    audio.load()

    print("Loading the voice...")
    voice.load()
    voice.warm_up()

    print("Starting the language model...")
    started = time.perf_counter()
    brain.start()
    print(f"  ready in {time.perf_counter() - started:.1f}s")

    _listener = wake.Listener(on_wake=_trigger)
    _listener.start()

    _hotkeys = keyboard.GlobalHotKeys({config.HOTKEY: _trigger})
    _hotkeys.start()

    threading.Thread(target=_watch_the_card, daemon=True).start()

    print(f'Ready. Say "{config.WAKE_WORD_NAME}", or press {config.HOTKEY}.')
    signals.ready.emit(config.WAKE_WORD_NAME)


def main() -> None:
    # do this before logging starts, else a second launch wipes the log
    if not _claim_single_instance():
        _say_already_running()
        return

    _start_logging()
    # before anything loads, or the models end up on the slow cores and speaking
    # runs at a fifth of the speed for the rest of the session
    print(f"Cores: {cores.use_the_fast_ones()}")
    settings.load()
    # where it thinks everything is, because models_folder is an absolute path
    # in settings.json and goes stale the moment anything moves
    print(f"Running from {paths.app_root()}")
    print(f"Models in {catalog.models_folder()}")

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

    def quit_aurix(icon=None) -> None:
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
        on_quit=lambda: quit_aurix(icon),
    )
    signals.open_panel.connect(panel.toggle)

    icon = tray.create(on_open=signals.open_panel.emit, on_quit=quit_aurix)
    threading.Thread(target=icon.run, daemon=True).start()

    overlay.show_starting()
    threading.Thread(target=_load_everything, daemon=True).start()

    try:
        sys.exit(app.exec())
    finally:
        brain.stop()


class _Tee:
    """Writes to the console and the log at once."""

    def __init__(self, *streams) -> None:
        self._streams = streams

    def write(self, text) -> None:
        for stream in self._streams:
            stream.write(text)

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()


def _start_logging() -> None:
    """Always write a log. Packaged there is no console to write to instead."""
    log = paths.log_file()
    try:
        if log.exists():
            log.replace(paths.previous_log_file())  # keep the run before this one
    except OSError:
        pass  # something has it open. Losing the old log is not worth not starting
    stream = open(log, "w", encoding="utf-8", buffering=1)
    if getattr(sys, "frozen", False):
        sys.stdout = sys.stderr = stream
        return
    sys.stdout = _Tee(sys.stdout, stream)
    sys.stderr = _Tee(sys.stderr, stream)


if __name__ == "__main__":
    main()
