"""The media keys, which work on whatever is playing without asking it."""

from pynput.keyboard import Controller, Key

_keyboard = Controller()

PLAY_PAUSE = Key.media_play_pause
NEXT = Key.media_next
PREVIOUS = Key.media_previous
LOUDER = Key.media_volume_up
QUIETER = Key.media_volume_down
MUTE = Key.media_volume_mute


def tap(key, times: int = 1) -> None:
    for _ in range(times):
        _keyboard.press(key)
        _keyboard.release(key)
