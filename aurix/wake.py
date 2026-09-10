"""Always-on wake word listening.

Nothing is transcribed or stored until the wake word fires. The listener
pauses itself while Aurix is recording or speaking, so it cannot wake itself.
"""

import threading

import sounddevice as sd
from openwakeword.model import Model

from . import config, paths, settings
from .audio import find_microphone


class Listener:
    """Watches the microphone for the wake word and calls back when it hears it."""

    def __init__(self, on_wake) -> None:
        self._on_wake = on_wake
        self._model = Model(
            wakeword_models=[str(paths.resolve(config.WAKE_MODEL))],
            melspec_model_path=str(paths.resolve(config.WAKE_MELSPEC)),
            embedding_model_path=str(paths.resolve(config.WAKE_EMBEDDING)),
            inference_framework="onnx",
        )
        self._name = list(self._model.models)[0]
        self._thread: threading.Thread | None = None
        self._running = False
        self._listening = threading.Event()

    @property
    def wake_word(self) -> str:
        return self._name

    def start(self) -> None:
        self._running = True
        self._listening.set()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._listening.set()  # let the loop wake up and exit

    def pause(self) -> None:
        """Stop listening - while Aurix is recording or talking."""
        self._listening.clear()

    def resume(self) -> None:
        """Start listening again, forgetting whatever was heard while paused."""
        self._model.reset()
        self._listening.set()

    def _loop(self) -> None:
        while self._running:
            if not self._listening.wait(timeout=0.2):
                continue
            self._listen_until_paused()

    def _listen_until_paused(self) -> None:
        with sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=config.WAKE_CHUNK,
            device=find_microphone(),
        ) as stream:
            while self._running and self._listening.is_set():
                block, _overflow = stream.read(config.WAKE_CHUNK)
                scores = self._model.predict(block.flatten())
                score = scores[self._name]

                if score >= settings.get("wake_threshold"):
                    self.pause()
                    self._on_wake()
                    return
