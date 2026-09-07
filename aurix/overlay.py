"""The on-screen orb: a frameless, click-through window at the top centre."""

import math

from PySide6.QtCore import QPointF, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QRadialGradient,
)
from PySide6.QtWidgets import QApplication, QWidget

from . import avatar, settings, voice

WIDTH = 400
HEIGHT = 170
MAX_HEIGHT = 420
ORB_CENTRE_Y = 62
ORB_RADIUS = 34
CAPTION_TOP = 104
FACE_SCALE = 0.72
TOP_MARGIN = 48

PALETTES = {
    "starting": ((120, 130, 170), (150, 160, 200), (100, 115, 160)),
    "listening": ((80, 160, 255), (140, 110, 255), (70, 220, 215)),
    "thinking": ((150, 110, 255), (230, 120, 200), (90, 150, 255)),
    "searching": ((255, 175, 70), (255, 210, 120), (240, 140, 90)),
    "done": ((90, 210, 160), (70, 190, 220), (120, 200, 190)),
}


class Overlay(QWidget):
    """The orb. Every method here must be called on the Qt thread."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.resize(WIDTH, HEIGHT)
        self._move_to_top_centre()

        self._phase = 0.0
        self._level = 0.0
        self._eased_level = 0.0
        self._caption = ""
        self._state = "listening"

        self._frames = QTimer(self)
        self._frames.setInterval(16)  # about 60 a second
        self._frames.timeout.connect(self._advance)

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(200)
        self._hides_when_faded = False

        self._auto_hide = QTimer(self)
        self._auto_hide.setSingleShot(True)
        self._auto_hide.timeout.connect(self.dismiss)

        self.setWindowOpacity(0.0)

    # --- placement ---

    def _move_to_top_centre(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.x() + (screen.width() - WIDTH) // 2,
            screen.y() + TOP_MARGIN,
        )

    # --- what Aurix tells it to do ---

    def begin_listening(self) -> None:
        self._state = "listening"
        self._caption = "Listening"
        self._level = 0.0
        self._eased_level = 0.0
        self._auto_hide.stop()
        self._move_to_top_centre()
        self.show()
        self._frames.start()
        self._fade_to(1.0)

    def show_starting(self) -> None:
        """Shown while the models load, which takes about half a minute."""
        self._state = "starting"
        self._caption = "Starting Aurix..."
        self._level = 0.0
        self._auto_hide.stop()
        self._move_to_top_centre()
        self.show()
        self._frames.start()
        self._fade_to(1.0)

    def show_ready(self, wake_word: str) -> None:
        self._state = "done"
        self._caption = f'Ready. Say "{wake_word}"'
        self._grow_to_fit()
        self._auto_hide.start(3200)

    def set_level(self, level: float) -> None:
        self._level = level

    def begin_thinking(self, heard: str) -> None:
        """Shows what was heard, so a mishearing is visible."""
        self._state = "thinking"
        self._caption = heard or "Didn't catch that"
        self._level = 0.0
        self._grow_to_fit()

    def show_result(self, text: str, hold_ms: int = 2600) -> None:
        self._state = "done"
        self._caption = text
        self._level = 0.0
        self._grow_to_fit()
        self._auto_hide.start(hold_ms)

    def begin_searching(self, what: str) -> None:
        self._state = "searching"
        self._caption = f"Looking up {what}"
        self._level = 0.0
        self._grow_to_fit()

    def begin_answer(self) -> None:
        """Start an answer that arrives in pieces."""
        self._state = "done"
        self._caption = ""
        self._level = 0.0
        self._auto_hide.stop()

    def append_answer(self, piece: str) -> None:
        self._caption += piece
        self._grow_to_fit()

    def finish_answer(self, hold_ms: int = 5000) -> None:
        self._auto_hide.start(hold_ms)

    def _grow_to_fit(self) -> None:
        """Grow taller for a long answer, up to MAX_HEIGHT."""
        metrics = QFontMetrics(QFont("Segoe UI", 11))
        box = metrics.boundingRect(
            0, 0, WIDTH - 60, 2000, Qt.TextWordWrap, self._caption or " "
        )
        wanted = CAPTION_TOP + max(box.height(), 20) + 24
        height = max(HEIGHT, min(wanted, MAX_HEIGHT))
        if height != self.height():
            self.resize(WIDTH, height)
            self._move_to_top_centre()

    def dismiss(self) -> None:
        self._auto_hide.stop()
        self._fade_to(0.0, then_hide=True)

    # --- animation ---

    def _fade_to(self, target: float, then_hide: bool = False) -> None:
        self._fade.stop()
        # Tracking this because disconnecting nothing spams warnings
        if self._hides_when_faded:
            self._fade.finished.disconnect(self._finish_hiding)
            self._hides_when_faded = False
        if then_hide:
            self._fade.finished.connect(self._finish_hiding)
            self._hides_when_faded = True
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(target)
        self._fade.start()

    def _finish_hiding(self) -> None:
        self._frames.stop()
        self.hide()

    def _advance(self) -> None:
        self._phase += 0.028
        # the microphone while you talk, the voice while it talks back
        heard = max(self._level, voice.speaking_level())
        # smooth it out or it flickers like mad
        self._eased_level += (heard - self._eased_level) * 0.22
        self.update()

    # --- drawing ---

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._paint_backdrop(painter)
        self._paint_face(painter)
        self._paint_caption(painter)

    def _paint_face(self, painter: QPainter) -> None:
        if settings.get("face") == "orb":
            self._paint_orb(painter)
            return
        avatar.paint(
            painter,
            QPointF(WIDTH / 2, ORB_CENTRE_Y),
            FACE_SCALE,
            self._state,
            self._eased_level,
            self._phase,
        )

    def _paint_backdrop(self, painter: QPainter) -> None:
        """A dark rounded panel, so the text stays readable on any wallpaper."""
        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(12, 12, -12, -12), 28, 28)
        painter.fillPath(path, QColor(16, 17, 24, 214))
        painter.setPen(QColor(255, 255, 255, 26))
        painter.drawPath(path)

    def _paint_orb(self, painter: QPainter) -> None:
        centre = QPointF(WIDTH / 2, ORB_CENTRE_Y)
        loudness = min(self._eased_level * 9.0, 1.0)
        # gentle breathing normally, bigger swell when you talk
        breath = 0.5 + 0.5 * math.sin(self._phase * 1.6)
        radius = ORB_RADIUS * (0.78 + 0.10 * breath + 0.24 * loudness)
        colours = PALETTES[self._state]

        painter.setPen(Qt.NoPen)

        halo = QColor(*colours[0])
        glow = QRadialGradient(centre, radius * 2.5)
        glow.setColorAt(0.0, QColor(halo.red(), halo.green(), halo.blue(), 80))
        glow.setColorAt(0.45, QColor(halo.red(), halo.green(), halo.blue(), 34))
        glow.setColorAt(1.0, QColor(halo.red(), halo.green(), halo.blue(), 0))
        painter.setBrush(glow)
        painter.drawEllipse(centre, radius * 2.5, radius * 2.5)

        # solid core first or it just looks like a blur
        core = QRadialGradient(centre, radius)
        core.setColorAt(0.0, QColor(halo.red(), halo.green(), halo.blue(), 255))
        core.setColorAt(0.70, QColor(halo.red(), halo.green(), halo.blue(), 232))
        core.setColorAt(0.92, QColor(halo.red(), halo.green(), halo.blue(), 120))
        core.setColorAt(1.0, QColor(halo.red(), halo.green(), halo.blue(), 0))
        painter.setBrush(core)
        painter.drawEllipse(centre, radius, radius)

        # 3 colours drifting around, 120 degrees apart so they cancel out
        # and the orb stays centred
        painter.setCompositionMode(QPainter.CompositionMode_Plus)
        drift = radius * (0.16 + 0.10 * loudness) * (0.6 + 0.4 * breath)
        for index, rgb in enumerate(colours):
            angle = self._phase + index * (2 * math.pi / 3)
            spot = QPointF(
                centre.x() + math.cos(angle) * drift,
                centre.y() + math.sin(angle) * drift,
            )
            colour = QColor(*rgb)
            blob = QRadialGradient(spot, radius * 0.92)
            blob.setColorAt(0.0, QColor(colour.red(), colour.green(), colour.blue(), 120))
            blob.setColorAt(0.6, QColor(colour.red(), colour.green(), colour.blue(), 48))
            blob.setColorAt(1.0, QColor(colour.red(), colour.green(), colour.blue(), 0))
            painter.setBrush(blob)
            painter.drawEllipse(spot, radius * 0.92, radius * 0.92)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        # highlight so it looks lit from somewhere
        highlight = QRadialGradient(
            QPointF(centre.x() - radius * 0.32, centre.y() - radius * 0.38), radius * 0.72
        )
        highlight.setColorAt(0.0, QColor(255, 255, 255, 150))
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(highlight)
        painter.drawEllipse(centre, radius, radius)

    def _paint_caption(self, painter: QPainter) -> None:
        if not self._caption:
            return
        painter.setPen(QColor(232, 236, 248))
        painter.setFont(QFont("Segoe UI", 11))
        painter.drawText(
            self.rect().adjusted(30, CAPTION_TOP, -30, -16),
            Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
            self._caption,
        )
