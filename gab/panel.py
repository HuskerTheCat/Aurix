"""The little panel that opens when you click the tray icon.

Everything here writes straight to settings.json, so a change survives a
restart and an installed copy can be configured without rebuilding it.
"""

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from . import audio, settings

WIDTH = 300
MARGIN = 12  # gap from the corner of the screen

STYLE = """
QWidget#panel {
    background: #14151c;
    border: 1px solid #2c2f3d;
    border-radius: 12px;
}
QLabel { color: #c9cfe0; font-family: 'Segoe UI'; font-size: 12px; }
QLabel#title { color: #eef1f8; font-size: 14px; font-weight: 600; }
QComboBox {
    background: #1e2029; color: #e8ecf8; border: 1px solid #33374a;
    border-radius: 6px; padding: 5px 8px; font-size: 12px;
}
QComboBox QAbstractItemView {
    background: #1e2029; color: #e8ecf8; selection-background-color: #3a5cc4;
}
QCheckBox { color: #c9cfe0; font-size: 12px; }
QPushButton {
    background: #232634; color: #e8ecf8; border: 1px solid #343849;
    border-radius: 6px; padding: 6px 10px; font-size: 12px;
}
QPushButton:hover { background: #2c3040; }
QPushButton#quit { color: #ffb4b4; }
QSlider::groove:horizontal {
    height: 4px; background: #2b2f3d; border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #5a8cff; width: 13px; height: 13px;
    margin: -5px 0; border-radius: 6px;
}
QSlider::sub-page:horizontal { background: #4a72d0; border-radius: 2px; }
"""


class Panel(QWidget):
    """Opens on a tray click, closes as soon as you click away."""

    def __init__(self, on_pause, on_stop_speaking, on_quit) -> None:
        super().__init__()
        self._on_pause = on_pause
        self._on_stop_speaking = on_stop_speaking
        self._on_quit = on_quit

        self.setObjectName("panel")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setStyleSheet(STYLE)
        self.setFixedWidth(WIDTH)

        self._build()

    # --- layout ---

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("Gab")
        title.setObjectName("title")
        layout.addWidget(title)

        layout.addWidget(QLabel("Microphone"))
        self._microphone = QComboBox()
        self._microphone.addItem("System default", None)
        for _index, name in audio.microphones():
            self._microphone.addItem(name, name)
        self._select_current_microphone()
        self._microphone.currentIndexChanged.connect(self._microphone_changed)
        layout.addWidget(self._microphone)

        self._volume_label = QLabel()
        layout.addWidget(self._volume_label)
        self._volume = self._slider(
            int(settings.get("volume") * 100), self._volume_changed
        )
        layout.addWidget(self._volume)
        self._show_volume()

        self._sensitivity_label = QLabel()
        layout.addWidget(self._sensitivity_label)
        self._sensitivity = self._slider(
            int(settings.get("wake_threshold") * 100), self._sensitivity_changed
        )
        layout.addWidget(self._sensitivity)
        self._show_sensitivity()

        self._paused = QCheckBox("Pause listening")
        self._paused.toggled.connect(self._on_pause)
        layout.addWidget(self._paused)

        buttons = QHBoxLayout()
        stop = QPushButton("Stop talking")
        stop.clicked.connect(self._on_stop_speaking)
        buttons.addWidget(stop)

        quit_button = QPushButton("Quit")
        quit_button.setObjectName("quit")
        quit_button.clicked.connect(self._on_quit)
        buttons.addWidget(quit_button)
        layout.addLayout(buttons)

    def _slider(self, value: int, on_change) -> QSlider:
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(5)
        slider.setMaximum(100)
        slider.setValue(value)
        slider.valueChanged.connect(on_change)
        return slider

    # --- reacting to changes ---

    def _select_current_microphone(self) -> None:
        chosen = settings.get("microphone")
        index = self._microphone.findData(chosen)
        self._microphone.setCurrentIndex(index if index >= 0 else 0)

    def _microphone_changed(self, _index: int) -> None:
        settings.put("microphone", self._microphone.currentData())

    def _volume_changed(self, value: int) -> None:
        settings.put("volume", value / 100)
        self._show_volume()

    def _show_volume(self) -> None:
        self._volume_label.setText(f"Volume - {self._volume.value()}%")

    def _sensitivity_changed(self, value: int) -> None:
        settings.put("wake_threshold", value / 100)
        self._show_sensitivity()

    def _show_sensitivity(self) -> None:
        # A low threshold wakes easily, so the friendlier label is inverted.
        eagerness = 100 - self._sensitivity.value()
        self._sensitivity_label.setText(f"Wake word sensitivity - {eagerness}%")

    # --- showing and hiding ---

    def toggle(self) -> None:
        if self.isVisible():
            self.hide()
            return
        self._select_current_microphone()
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
        # Clicking anywhere else puts it away, the way a tray menu behaves.
        if incoming.type() == QEvent.WindowDeactivate:
            self.hide()
        return super().event(incoming)
