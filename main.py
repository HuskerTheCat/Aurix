"""Gab - step one: prove the audio path.

Runs in the tray. Press the hotkey, speak, and see what Gab heard.
The wake word, the answers and the voice all get built on top of this.
"""

import threading
import time

from pynput import keyboard

from gab import audio, config, speech, tray
from gab.audio import NoSpeechDetected, record_until_silence

_busy = threading.Lock()


def _handle_request() -> None:
    """One full listen-and-transcribe cycle."""
    if not _busy.acquire(blocking=False):
        return  # already listening, ignore the extra press
    try:
        print("\nListening...")
        started = time.perf_counter()

        try:
            audio = record_until_silence()
        except NoSpeechDetected as error:
            print(f"  heard nothing - {error}")
            return

        recorded = time.perf_counter()
        text = speech.transcribe(audio)
        finished = time.perf_counter()

        print(f'  heard: "{text}"' if text else "  heard: (nothing recognisable)")
        print(
            f"  {len(audio) / config.SAMPLE_RATE:.1f}s audio"
            f"  |  transcribe {finished - recorded:.2f}s"
            f"  |  total {finished - started:.2f}s"
        )
    finally:
        _busy.release()


def _on_hotkey() -> None:
    """Run the work off the key listener thread so hotkeys stay responsive."""
    threading.Thread(target=_handle_request, daemon=True).start()


def main() -> None:
    print("Loading the speech model (the first run downloads it)...")
    speech.load()

    print("Measuring the room, stay quiet for a moment...")
    print(f"Speech threshold set to {audio.calibrate():.5f}")

    print(f"Ready. Press {config.HOTKEY} and speak.")
    print("Quit from the tray icon, or press Ctrl+C here.")

    hotkeys = keyboard.GlobalHotKeys({config.HOTKEY: _on_hotkey})
    hotkeys.start()

    def quit_gab(icon) -> None:
        hotkeys.stop()
        icon.stop()

    tray.create(on_quit=quit_gab).run()


if __name__ == "__main__":
    main()
