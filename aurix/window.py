"""The full settings window, opened from the tray panel."""

import os
import shutil
import threading
import time
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import (
    audio, brain, catalog, config, download, memory, paths, search, settings,
    theme, timings, voice,
)
from .switch import Switch

SAMPLE = "This is how I sound. Ask me anything."
HEADER = 52  # the strip at the top you can drag the window by

# Left on the card for the desktop and everything else, so a model that fits by
# a hair is not called a fit.
CARD_HEADROOM_MB = 512


def _size(byte_count: int) -> str:
    if byte_count >= 1_000_000_000:
        return f"{byte_count / 1_000_000_000:.1f} GB"
    return f"{byte_count / 1_000_000:.0f} MB"


def _without_your_name(path) -> str:
    """The folder, with the home directory written the short way.

    This window is the thing people screenshot when something is wrong, and
    there is no reason to put their username in it. Longest match first, since
    LOCALAPPDATA lives inside USERPROFILE.
    """
    text = str(path)
    for variable in ("LOCALAPPDATA", "APPDATA", "USERPROFILE"):
        root = os.environ.get(variable)
        if root and text.lower().startswith(root.lower()):
            return f"%{variable}%" + text[len(root):]
    return text


def _bigger_model_verdict(card: dict) -> str | None:
    """Whether a bigger model would fit, said plainly instead of in numbers.

    What this model actually cost on this card is known, so the guess for a
    bigger one is scaled from that rather than from a rule of thumb.
    """
    if not card.get("card_mb") or not card.get("vram_mb"):
        return None

    chosen = catalog.chosen_model()
    bigger = sorted(
        (model for model in catalog.MODELS if model.size > chosen.size),
        key=lambda model: model.size,
    )
    if not bigger:
        return "This is the biggest model on the list, so there is nowhere to go up."

    per_byte = card["vram_mb"] / (chosen.size / 1_048_576)
    room = card["card_mb"] - CARD_HEADROOM_MB
    fits = [model for model in bigger if (model.size / 1_048_576) * per_byte <= room]

    if not fits:
        spare = card["card_mb"] - card["vram_mb"]
        return f"No room for a bigger model - about {spare:.0f} MB spare on the card."
    return f"Your card has room for {fits[-1].name}."


def _last_lookup_line() -> str:
    """The last thing that left this machine, so the privacy claim is checkable."""
    looked_up = search.last_lookup()
    if looked_up is None:
        return "Nothing has left this machine this session."

    query, when = looked_up
    ago = time.time() - when
    if ago < 5:
        since = "just now"
    elif ago < 90:
        since = f"{ago:.0f} seconds ago"
    else:
        since = f"{ago / 60:.0f} minutes ago"
    return f'Last thing looked up, {since}: "{query}"'


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
        # only models have a size worth showing - every voice is in the one file
        title = f"{item.name}  -  {_size(item.size)}" if isinstance(item, catalog.Model) else item.name
        self._name = QLabel(title)
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

        self.setWindowTitle("Aurix")
        self.setObjectName("settings")
        self.setFixedSize(740, 640)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(theme.stylesheet())
        self._dragging_from = None

        self.progress.connect(self._on_progress)
        self.finished.connect(self._on_finished)
        self.switched.connect(self._on_switched)
        self.moved.connect(self._on_moved)

        self._build()
        self._filler.set_colours(*theme.switch_colours())

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        shell = QFrame()
        shell.setObjectName("shell")
        outer.addWidget(shell)

        layout = QVBoxLayout(shell)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        heading = QHBoxLayout()
        title = QLabel("Aurix settings")
        title.setObjectName("title")
        heading.addWidget(title)
        heading.addStretch(1)
        close = QPushButton("✕")
        close.setObjectName("close")
        close.setFixedSize(28, 28)
        close.clicked.connect(self.hide)
        heading.addWidget(close)
        layout.addLayout(heading)

        tabs = QTabWidget()
        tabs.addTab(self._model_tab(), "Model")
        tabs.addTab(self._voice_tab(), "Voice")
        tabs.addTab(self._audio_tab(), "Audio")
        tabs.addTab(self._look_tab(), "Look")
        tabs.addTab(self._memory_tab(), "Memory")
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
            self._dim("Preview plays a line so you can hear it first. They all sound "
                      "like Aurix - the robot voice goes on top of whichever you pick, "
                      "and it was built around Heart.")
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
            # the slider is sensitivity, which is the inverse of the threshold. It used
            # to move the handle by the threshold while labelling it as the
            # sensitivity, so dragging right made it less sensitive while the
            # number went down. Invisible at 0.5, obvious at anything else.
            "Wake word sensitivity", 5, 95, 100 - int(settings.get("wake_threshold") * 100),
            lambda value: settings.put("wake_threshold", (100 - value) / 100),
            lambda value: f"Wake word sensitivity - {value}%",
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
            self._dim("How long you can go quiet mid-sentence before Aurix decides "
                      "you are finished. Raise it if you get cut off.")
        )

        self._fun = Switch("Fun mode")
        self._fun.setChecked(settings.get("fun_mode"))
        self._fun.toggled.connect(lambda on: settings.put("fun_mode", on))
        column.addWidget(self._fun)
        column.addWidget(
            self._dim("Chattier and more of a character. Turn it off and answers "
                      "go back to one or two flat sentences, which is quicker to "
                      "say out loud.")
        )

        self._filler = Switch("Say something while it thinks")
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

        column.addWidget(self._label("Face"))
        self._face = QComboBox()
        self._face.addItem("Protogen", "protogen")
        self._face.addItem("Orb", "orb")
        chosen_face = self._face.findData(settings.get("face"))
        self._face.setCurrentIndex(chosen_face if chosen_face >= 0 else 0)
        self._face.currentIndexChanged.connect(
            lambda _i: settings.put("face", self._face.currentData())
        )
        column.addWidget(self._face)
        column.addWidget(
            self._dim("The protogen is a placeholder drawn in code until there "
                      "is real art. The orb is what it used to be.")
        )

        column.addStretch(1)
        return tab

    def _memory_tab(self) -> QWidget:
        tab = QWidget()
        column = QVBoxLayout(tab)
        column.setContentsMargins(14, 14, 14, 14)
        column.setSpacing(10)

        column.addWidget(self._label("What Aurix knows about you"))
        column.addWidget(
            self._dim("One thing per line. Aurix adds to this by itself when you "
                      "tell it something about you, and you can write, change or "
                      "delete any of it here. It never leaves this machine.")
        )

        self._memory = QPlainTextEdit()
        self._memory.setPlaceholderText(
            "Nothing yet. Tell Aurix something about yourself, or type it here."
        )
        column.addWidget(self._memory, 1)

        self._memory_note = self._dim("")
        column.addWidget(self._memory_note)

        row = QHBoxLayout()
        save = QPushButton("Save")
        save.setObjectName("primary")
        save.clicked.connect(self._save_memory)
        row.addWidget(save)
        reload_it = QPushButton("Undo my changes")
        reload_it.clicked.connect(self._load_memory)
        row.addWidget(reload_it)
        row.addStretch(1)
        clear = QPushButton("Forget everything")
        clear.setObjectName("quit")
        clear.clicked.connect(self._clear_memory)
        row.addWidget(clear)
        column.addLayout(row)

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
        forget = QPushButton("Forget the conversation")
        forget.clicked.connect(self._forget)
        row.addWidget(forget)
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

    def _forget(self) -> None:
        brain.forget()
        self._note.setText("Forgotten. The next question starts fresh.")

    # --- what it remembers about you ---

    def _load_memory(self) -> None:
        """Show what is on disk, throwing away anything typed and not saved."""
        self._memory.setPlainText(memory.text())
        self._memory.document().setModified(False)
        self._memory_note.setText(self._memory_count())

    def _memory_count(self) -> str:
        count = len(memory.notes())
        if not count:
            return "Nothing remembered yet."
        room = config.MEMORY_NOTES
        return f"{count} of {room} things remembered."

    def _save_memory(self) -> None:
        memory.replace(self._memory.toPlainText())
        # read it back, because saving trims blank lines, over-long lines and
        # anything past the limit - better to see that happen than not
        self._load_memory()
        self._note.setText("Saved. Aurix will know that from the next question.")

    def _clear_memory(self) -> None:
        confirm = QMessageBox(self)
        confirm.setWindowTitle("Forget everything")
        confirm.setText("Delete everything Aurix remembers about you?")
        confirm.setInformativeText("This cannot be undone.")
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        confirm.setDefaultButton(QMessageBox.Cancel)
        if confirm.exec() != QMessageBox.Yes:
            return
        memory.clear()
        self._load_memory()
        self._note.setText("Forgotten. Aurix no longer knows anything about you.")

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
            target=voice.preview, args=(item.key, SAMPLE), daemon=True
        ).start()

    def _download(self, item) -> None:
        self._cancel[item.key] = False
        self._cards[item.key].show_progress(0)
        self._note.setText(f"Downloading {item.name}, {_size(item.size)}.")
        threading.Thread(target=self._download_worker, args=(item,), daemon=True).start()

    def _cancel_download(self, item) -> None:
        self._cancel[item.key] = True

    def _download_worker(self, item) -> None:
        """Only models are ever downloaded - the voices ship with the app."""
        try:
            download.fetch(
                item.url,
                catalog.model_file(item),
                item.size,
                lambda done: self.progress.emit(item.key, done),
                lambda: self._cancel[item.key],
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
        self._filler.set_colours(*theme.switch_colours())
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
        # through the catalog, not the raw setting - an upgraded install still
        # names a Piper voice, and comparing against that highlighted nothing
        for model in catalog.MODELS:
            self._cards[model.key].refresh(catalog.chosen_model().key)
        for item in catalog.VOICES:
            self._cards[item.key].refresh(catalog.chosen_voice().key)

        folder = catalog.models_folder()
        free = download.free_space(folder)
        self._folder_line.setText(
            f"Kept in {_without_your_name(folder)}  -  {_size(free)} free"
        )
        self._status.setText(self._status_text())

        # not while something is half typed - Aurix writing a note of its own
        # must not wipe out what somebody is in the middle of editing
        if not self._memory.document().isModified():
            self._load_memory()

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

            verdict = _bigger_model_verdict(card)
            if verdict is not None:
                lines.append(verdict)

        in_use = brain.memory_mb()
        if in_use is not None:
            lines.append(f"Memory in use right now: {in_use / 1024:.1f} GB")

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

        took = timings.last()
        if took:
            lines.append(
                f"Silence before it spoke: {took['quiet']:.2f}s "
                f"(heard you in {took['transcribe']:.2f}s, "
                f"answer written in {took['written']:.2f}s)"
            )

        lines.append("")
        lines.append(_last_lookup_line())

        lines.append("")
        lines.append(f"Model: {catalog.chosen_model().name} - {settings.get('model')}")
        lines.append(f"Voice: {catalog.chosen_voice().name}")
        keys = config.HOTKEY.replace("<", "").replace(">", "").replace("+", " + ").title()
        lines.append(f'Wake word: "{config.WAKE_WORD_NAME}", or press {keys}')
        lines.append(f"Version: {config.VERSION}")
        return "\n".join(lines)

    def open(self) -> None:
        self._refresh()
        if self._dragging_from is None and not self.isVisible():
            self._centre()
        self.show()
        self.raise_()
        self.activateWindow()

    def _centre(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.center() - self.rect().center())

    # --- dragging it around, since there is no title bar to grab ---

    def mousePressEvent(self, event) -> None:
        if event.position().y() <= HEADER:
            self._dragging_from = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event) -> None:
        if self._dragging_from is not None:
            self.move(event.globalPosition().toPoint() - self._dragging_from)

    def mouseReleaseEvent(self, _event) -> None:
        self._dragging_from = None
