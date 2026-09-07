"""The little panel that opens from the tray icon."""

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from . import config, settings, theme

WIDTH = 300
MARGIN = 12  # gap from the corner of the screen


class Panel(QWidget):
    """Opens on a tray click, closes as soon as you click away."""

    def __init__(self, on_pause, on_stop_speaking, on_settings, on_quit) -> None:
        super().__init__()
        self._on_pause = on_pause
        self._on_stop_speaking = on_stop_speaking
        self._on_settings = on_settings
        self._on_quit = on_quit

        self.setObjectName("panel")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(theme.stylesheet())
        self.setFixedWidth(WIDTH)

        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("Gab")
        title.setObjectName("title")
        layout.addWidget(title)

        # mostly you just open this to remember the wake word
        wake_word = QLabel(f'Say  "{config.WAKE_WORD_NAME}"')
        wake_word.setObjectName("wakeword")
        wake_word.setAlignment(Qt.AlignCenter)
        layout.addWidget(wake_word)

        self._volume_label = QLabel()
        layout.addWidget(self._volume_label)
        self._volume = QSlider(Qt.Horizontal)
        self._volume.setMinimum(5)
        self._volume.setMaximum(100)
        self._volume.setValue(int(settings.get("volume") * 100))
        self._volume.valueChanged.connect(self._volume_changed)
        layout.addWidget(self._volume)
        self._show_volume()

        self._paused = QCheckBox("Pause listening")
        self._paused.toggled.connect(self._on_pause)
        layout.addWidget(self._paused)

        everything = QPushButton("Settings")
        everything.setObjectName("primary")
        everything.clicked.connect(self._open_settings)
        layout.addWidget(everything)

        buttons = QHBoxLayout()
        stop = QPushButton("Stop talking")
        stop.clicked.connect(self._on_stop_speaking)
        buttons.addWidget(stop)

        quit_button = QPushButton("Quit")
        quit_button.setObjectName("quit")
        quit_button.clicked.connect(self._on_quit)
        buttons.addWidget(quit_button)
        layout.addLayout(buttons)

    def _open_settings(self) -> None:
        self.hide()
        self._on_settings()

    def _volume_changed(self, value: int) -> None:
        settings.put("volume", value / 100)
        self._show_volume()

    def _show_volume(self) -> None:
        self._volume_label.setText(f"Volume - {self._volume.value()}%")

    def restyle(self) -> None:
        """Called when the colours change in the settings window."""
        self.setStyleSheet(theme.stylesheet())

    def toggle(self) -> None:
        if self.isVisible():
            self.hide()
            return
        self._volume.setValue(int(settings.get("volume") * 100))
        self._move_near_tray()
        self.show()
        self.raise_()
        self.activateWindow()

    def _move_near_tray(self) -> None:
        """Bottom right, above where the tray icons live."""
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(
            screen.right() - self.width() - MARGIN,
            screen.bottom() - self.height() - MARGIN,
        )

    def event(self, incoming) -> bool:
        # click away to close it, like a normal tray menu
        if incoming.type() == QEvent.WindowDeactivate:
            self.hide()
        return super().event(incoming)
