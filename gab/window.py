"""The full settings window, opened from the tray panel."""

import os
import shutil
import threading
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import audio, brain, catalog, config, download, paths, settings, theme, voice

SAMPLE = "This is how I sound. Ask me anything."


def _size(byte_count: int) -> str:
    if byte_count >= 1_000_000_000:
        return f"{byte_count / 1_000_000_000:.1f} GB"
    return f"{byte_count / 1_000_000:.0f} MB"


class Card(QFrame):
    """One model or voice, with whatever button makes sense right now."""

    def __init__(self, item, on_use, on_download, on_cancel, on_preview=None) -> None:
        super().__init__()
        self._item = item
        self.setObjectName("card")

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(12)

        words = QVBoxLayout()
        words.setSpacing(2)
        self._name = QLabel(f"{item.name}  -  {_size(item.size)}")
        self._name.setObjectName("heading")
        words.addWidget(self._name)
        note = QLabel(item.note)
        note.setObjectName("dim")
        note.setWordWrap(True)
        words.addWidget(note)
        self._progress = QProgressBar()
        self._progress.setRange(0, 1000)
        self._progress.hide()
        words.addWidget(self._progress)
        row.addLayout(words, 1)

        self._preview = QPushButton("Preview")
        self._preview.setVisible(on_preview is not None)
        if on_preview is not None:
            self._preview.clicked.connect(lambda: on_preview(item))
        row.addWidget(self._preview)

        self._action = QPushButton()
        self._action.clicked.connect(self._clicked)
        row.addWidget(self._action)

        self._on_use = on_use
        self._on_download = on_download
        self._on_cancel = on_cancel
        self._busy = False

    def _clicked(self) -> None:
        if self._busy:
            self._on_cancel(self._item)
        elif catalog.is_installed(self._item):
            self._on_use(self._item)
        else:
            self._on_download(self._item)

    def refresh(self, chosen_key: str) -> None:
        installed = catalog.is_installed(self._item)
        chosen = self._item.key == chosen_key

        self.setProperty("chosen", "true" if chosen else "false")
        self.style().unpolish(self)
        self.style().polish(self)

        self._preview.setEnabled(installed and not self._busy)
        self._action.setEnabled(not chosen or self._busy)

        if self._busy:
            self._action.setText("Cancel")
        elif chosen:
            self._action.setText("In use")
        elif installed:
            self._action.setText("Use this")
        else:
            self._action.setText("Download")

    def show_progress(self, done: int) -> None:
        self._busy = True
        self._progress.show()
        self._progress.setValue(int(1000 * done / self._item.size))
        self._progress.setFormat(f"{_size(done)} of {_size(self._item.size)}")
        self._action.setText("Cancel")
        self._action.setEnabled(True)
        self._preview.setEnabled(False)

    def clear_progress(self) -> None:
        self._busy = False
        self._progress.hide()


class Window(QWidget):
    """Everything the tray panel is too small for."""

    progress = Signal(str, int)
    finished = Signal(str, str)
    switched = Signal(str)
    moved = Signal(str)

    def __init__(self, apply_model, on_theme) -> None:
        super().__init__()
        self._apply_model = apply_model
        self._on_theme = on_theme

        self._cards: dict[str, Card] = {}
        self._cancel: dict[str, bool] = {}

        self.setWindowTitle("Gab")
        self.resize(720, 620)
        self.setStyleSheet(theme.stylesheet())

        self.progress.connect(self._on_progress)
        self.finished.connect(self._on_finished)
        self.switched.connect(self._on_switched)
        self.moved.connect(self._on_moved)

        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(12)

        title = QLabel("Gab settings")
        title.setObjectName("title")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._model_tab(), "Model")
        tabs.addTab(self._voice_tab(), "Voice")
        tabs.addTab(self._audio_tab(), "Audio")
        tabs.addTab(self._look_tab(), "Look")
        tabs.addTab(self._status_tab(), "Status")
        tabs.currentChanged.connect(lambda _index: self._refresh())
        layout.addWidget(tabs, 1)

        self._note = QLabel("")
        self._note.setObjectName("dim")
        self._note.setWordWrap(True)
        layout.addWidget(self._note)

    # --- the tabs ---

    def _scrolling(self, items, on_preview=None) -> QScrollArea:
        holder = QWidget()
        column = QVBoxLayout(holder)
        column.setContentsMargins(0, 0, 8, 0)
        column.setSpacing(8)

        for item in items:
            card = Card(item, self._use, self._download, self._cancel_download, on_preview)
            self._cards[item.key] = card
            column.addWidget(card)
        column.addStretch(1)

        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(holder)
        return area

    def _model_tab(self) -> QWidget:
        tab = QWidget()
        column = QVBoxLayout(tab)
        column.setContentsMargins(14, 14, 14, 14)
        column.setSpacing(10)

        column.addWidget(
            self._dim("Bigger models know more and get things right more often. "
                      "Switching one takes a few seconds while it loads.")
        )
        column.addWidget(self._scrolling(catalog.MODELS), 1)

        folder = QHBoxLayout()
        self._folder_line = QLabel()
        self._folder_line.setObjectName("dim")
        self._folder_line.setWordWrap(True)
        folder.addWidget(self._folder_line, 1)
        change = QPushButton("Change folder")
        change.clicked.connect(self._choose_folder)
        folder.addWidget(change)
        column.addLayout(folder)

        return tab

    def _voice_tab(self) -> QWidget:
        tab = QWidget()
        column = QVBoxLayout(tab)
        column.setContentsMargins(14, 14, 14, 14)
        column.setSpacing(10)

        column.addWidget(
            self._dim("Preview plays a line so you can hear it first. The quick ones "
                      "start talking about a second sooner than the natural ones.")
        )
        column.addWidget(self._scrolling(catalog.VOICES, on_preview=self._preview), 1)
        return tab

    def _audio_tab(self) -> QWidget:
        tab = QWidget()
        column = QVBoxLayout(tab)
        column.setContentsMargins(14, 14, 14, 14)
        column.setSpacing(10)

        column.addWidget(self._label("Microphone"))
        self._microphone = QComboBox()
        self._microphone.addItem("System default", None)
        for _index, name in audio.microphones():
            self._microphone.addItem(name, name)
        index = self._microphone.findData(settings.get("microphone"))
        self._microphone.setCurrentIndex(index if index >= 0 else 0)
        self._microphone.currentIndexChanged.connect(
            lambda _i: settings.put("microphone", self._microphone.currentData())
        )
        column.addWidget(self._microphone)

        self._volume, self._volume_label = self._dial(
            "Speaking volume", 5, 100, int(settings.get("volume") * 100),
            lambda value: settings.put("volume", value / 100),
            lambda value: f"Speaking volume - {value}%",
        )
        column.addWidget(self._volume_label)
        row = QHBoxLayout()
        row.addWidget(self._volume, 1)
        test = QPushButton("Test")
        test.clicked.connect(lambda: self._say(SAMPLE))
        row.addWidget(test)
        column.addLayout(row)

        self._sensitivity, self._sensitivity_label = self._dial(
            "Wake word sensitivity", 5, 100, int(settings.get("wake_threshold") * 100),
            lambda value: settings.put("wake_threshold", value / 100),
            lambda value: f"Wake word sensitivity - {100 - value}%",
        )
        column.addWidget(self._sensitivity_label)
        column.addWidget(self._sensitivity)
        column.addWidget(
            self._dim("Higher means it wakes more easily, and gets set off more often.")
        )

        self._hangover, self._hangover_label = self._dial(
            "Pause before it answers", 4, 25, int(settings.get("silence_hangover") * 10),
            lambda value: settings.put("silence_hangover", value / 10),
            lambda value: f"Pause before it answers - {value / 10:.1f}s",
        )
        column.addWidget(self._hangover_label)
        column.addWidget(self._hangover)
        column.addWidget(
            self._dim("How long you can go quiet mid-sentence before Gab decides "
                      "you are finished. Raise it if you get cut off.")
        )

        self._filler = QCheckBox("Say something while it thinks")
        self._filler.setChecked(settings.get("think_out_loud"))
        self._filler.toggled.connect(
            lambda on: settings.put("think_out_loud", on)
        )
        column.addWidget(self._filler)
        column.addWidget(
            self._dim("A quick \"hmm\" the moment you finish asking, so it does not "
                      "sit there in silence while it works the answer out.")
        )

        column.addStretch(1)
        return tab

    def _look_tab(self) -> QWidget:
        tab = QWidget()
        column = QVBoxLayout(tab)
        column.setContentsMargins(14, 14, 14, 14)
        column.setSpacing(10)

        column.addWidget(self._label("Colours"))
        self._theme = QComboBox()
        for key, palette in theme.THEMES.items():
            self._theme.addItem(palette["name"], key)
        chosen = self._theme.findData(settings.get("theme"))
        self._theme.setCurrentIndex(chosen if chosen >= 0 else 0)
        self._theme.currentIndexChanged.connect(self._theme_changed)
        column.addWidget(self._theme)

        column.addWidget(self._dim("The orb keeps its own colours for now."))
        column.addStretch(1)
        return tab

    def _status_tab(self) -> QWidget:
        tab = QWidget()
        column = QVBoxLayout(tab)
        column.setContentsMargins(14, 14, 14, 14)
        column.setSpacing(10)

        self._status = QLabel()
        self._status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._status.setWordWrap(True)
        column.addWidget(self._status)
        column.addStretch(1)

        row = QHBoxLayout()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self._refresh)
        row.addWidget(refresh)
        logs = QPushButton("Open log folder")
        logs.clicked.connect(lambda: os.startfile(paths.log_file().parent))
        row.addWidget(logs)
        row.addStretch(1)
        column.addLayout(row)

        return tab

    # --- small pieces ---

    def _label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("heading")
        return label

    def _dim(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("dim")
        label.setWordWrap(True)
        return label

    def _dial(self, name, low, high, value, on_change, describe):
        label = QLabel(describe(value))
        label.setObjectName("heading")
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(low)
        slider.setMaximum(high)
        slider.setValue(value)

        def changed(new: int) -> None:
            on_change(new)
            label.setText(describe(new))

        slider.valueChanged.connect(changed)
        return slider, label

    def _say(self, text: str) -> None:
        threading.Thread(target=voice.speak, args=(text,), daemon=True).start()

    # --- what the buttons do ---

    def _use(self, item) -> None:
        if isinstance(item, catalog.Model):
            settings.put("model", item.key)
            self._note.setText(f"Loading {item.name}. This takes a moment.")
            threading.Thread(target=self._switch_model, daemon=True).start()
        else:
            settings.put("voice", item.key)
            voice.load()
            self._note.setText(f"Now speaking as {item.name}.")
        self._refresh()

    def _switch_model(self) -> None:
        try:
            self._apply_model()
        except Exception as error:  # noqa: BLE001 - show it, do not crash the app
            self.switched.emit(str(error))
            return
        self.switched.emit("")

    def _preview(self, item) -> None:
        threading.Thread(
            target=voice.preview, args=(catalog.voice_file(item), SAMPLE), daemon=True
        ).start()

    def _download(self, item) -> None:
        self._cancel[item.key] = False
        self._cards[item.key].show_progress(0)
        self._note.setText(f"Downloading {item.name}, {_size(item.size)}.")
        threading.Thread(target=self._download_worker, args=(item,), daemon=True).start()

    def _cancel_download(self, item) -> None:
        self._cancel[item.key] = True

    def _download_worker(self, item) -> None:
        is_model = isinstance(item, catalog.Model)
        target = catalog.model_file(item) if is_model else catalog.voice_file(item)
        try:
            download.fetch(
                item.url,
                target,
                item.size,
                lambda done: self.progress.emit(item.key, done),
                lambda: self._cancel[item.key],
            )
            if not is_model:
                download.fetch_small(
                    item.url + ".json", target.with_name(target.name + ".json")
                )
        except download.Cancelled:
            self.finished.emit(item.key, "cancelled")
            return
        except Exception as error:  # noqa: BLE001 - show it, do not crash the app
            self.finished.emit(item.key, str(error))
            return
        self.finished.emit(item.key, "")

    def _choose_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, "Where to keep models", settings.get("models_folder")
        )
        if not chosen or Path(chosen) == catalog.models_folder():
            return
        self._note.setText("Moving the models across. This can take a while.")
        threading.Thread(target=self._move_worker, args=(chosen,), daemon=True).start()

    def _move_worker(self, chosen: str) -> None:
        old = catalog.models_folder()
        new = Path(chosen)
        try:
            new.mkdir(parents=True, exist_ok=True)
            for model in old.glob("*.gguf"):
                shutil.move(str(model), str(new / model.name))
        except Exception as error:  # noqa: BLE001 - show it, do not crash the app
            self.moved.emit(str(error))
            return
        settings.put("models_folder", str(new))
        self.moved.emit("")

    def _theme_changed(self, _index: int) -> None:
        settings.put("theme", self._theme.currentData())
        self.setStyleSheet(theme.stylesheet())
        self._on_theme()
        self._refresh()

    # --- news from the worker threads ---

    def _on_progress(self, key: str, done: int) -> None:
        self._cards[key].show_progress(done)

    def _on_finished(self, key: str, error: str) -> None:
        self._cards[key].clear_progress()
        if error == "cancelled":
            self._note.setText("Download stopped.")
        elif error:
            self._note.setText(f"That download failed: {error}")
        else:
            self._note.setText("Downloaded. Press Use this to switch to it.")
        self._refresh()

    def _on_switched(self, error: str) -> None:
        self._note.setText(f"The model would not load: {error}" if error else "Ready.")
        self._refresh()

    def _on_moved(self, error: str) -> None:
        self._note.setText(f"Could not move them: {error}" if error else "Models moved.")
        self._refresh()

    # --- keeping the screen honest ---

    def _refresh(self) -> None:
        for model in catalog.MODELS:
            self._cards[model.key].refresh(settings.get("model"))
        for item in catalog.VOICES:
            self._cards[item.key].refresh(settings.get("voice"))

        folder = catalog.models_folder()
        free = download.free_space(folder)
        self._folder_line.setText(f"Kept in {folder}  -  {_size(free)} free")
        self._status.setText(self._status_text())

    def _status_text(self) -> str:
        lines = []

        card = brain.hardware()
        if not card:
            lines.append("Graphics card: still starting up")
        elif not card.get("layers"):
            lines.append(
                "Graphics card: not being used. Everything is running on the "
                "processor, so answers will be slow. Try a smaller model."
            )
        else:
            lines.append(f"Graphics card: {card.get('device', 'in use')}")
            lines.append(
                f"Layers on the card: {card['layers']} of {card['of_layers']}"
            )
            if card.get("vram_mb"):
                using = f"{card['vram_mb'] / 1024:.1f} GB"
                if card.get("card_mb"):
                    using += f" of {card['card_mb'] / 1024:.1f} GB"
                lines.append(f"Video memory: {using}")

        last = brain.last_answer()
        if last:
            speed = last["words"] / last["seconds"]
            lines.append(
                f"Last answer: {last['words']} words in {last['seconds']:.1f}s "
                f"({speed:.1f} words a second)"
            )
            if last["looked_up"] != "direct":
                lines.append(f"It looked that one up first ({last['looked_up']}).")
        else:
            lines.append("Last answer: nothing asked yet")

        lines.append("")
        lines.append(f"Model: {catalog.chosen_model().name} - {settings.get('model')}")
        lines.append(f"Voice: {catalog.chosen_voice().name}")
        keys = config.HOTKEY.replace("<", "").replace(">", "").replace("+", " + ").title()
        lines.append(f'Wake word: "{config.WAKE_WORD_NAME}", or press {keys}')
        lines.append(f"Version: {config.VERSION}")
        return "\n".join(lines)

    def open(self) -> None:
        self._refresh()
        self.show()
        self.raise_()
        self.activateWindow()
