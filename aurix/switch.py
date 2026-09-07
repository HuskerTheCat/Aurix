"""A sliding on/off switch, because Qt does not come with one.

A tick box tells you the state but not that it is a thing you flip. This is the
same idea drawn as a track with a knob that slides across when clicked.
"""

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
)
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractButton

TRACK_W = 42
TRACK_H = 22
KNOB = 16
GAP = 10  # between the switch and its label


class Switch(QAbstractButton):
    """Checkable, so it behaves exactly like the checkbox it replaces."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)

        self._travel = 0.0  # 0 is off, 1 is on
        self._slide = QPropertyAnimation(self, b"travel", self)
        self._slide.setDuration(140)
        self._slide.setEasingCurve(QEasingCurve.OutCubic)

        # Set by the stylesheet, since the palette changes with the theme.
        self._on_colour = QColor(90, 140, 255)
        self._off_colour = QColor(60, 64, 80)
        self._knob_colour = QColor(240, 243, 250)
        self._text_colour = QColor(201, 207, 224)

        self.toggled.connect(self._slide_to)

    # --- colours, so themes can drive it ---

    def set_colours(self, on: str, off: str, knob: str, text: str) -> None:
        self._on_colour = QColor(on)
        self._off_colour = QColor(off)
        self._knob_colour = QColor(knob)
        self._text_colour = QColor(text)
        self.update()

    # --- the animated bit ---

    def _get_travel(self) -> float:
        return self._travel

    def _set_travel(self, value: float) -> None:
        self._travel = value
        self.update()

    travel = Property(float, _get_travel, _set_travel)

    def _slide_to(self, on: bool) -> None:
        self._slide.stop()
        self._slide.setStartValue(self._travel)
        self._slide.setEndValue(1.0 if on else 0.0)
        self._slide.start()

    # --- size and drawing ---

    def sizeHint(self) -> QSize:
        width = TRACK_W + (GAP + self.fontMetrics().horizontalAdvance(self.text())
                           if self.text() else 0)
        return QSize(width, max(TRACK_H, self.fontMetrics().height()))

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        middle = self.height() / 2
        track = QRectF(0, middle - TRACK_H / 2, TRACK_W, TRACK_H)

        colour = QColor(self._off_colour)
        if self._travel:
            wanted = self._on_colour
            colour = QColor(
                round(colour.red() + (wanted.red() - colour.red()) * self._travel),
                round(colour.green() + (wanted.green() - colour.green()) * self._travel),
                round(colour.blue() + (wanted.blue() - colour.blue()) * self._travel),
            )

        painter.setPen(Qt.NoPen)
        painter.setBrush(colour)
        painter.drawRoundedRect(track, TRACK_H / 2, TRACK_H / 2)

        edge = (TRACK_H - KNOB) / 2
        left = edge + self._travel * (TRACK_W - KNOB - edge * 2)
        painter.setBrush(self._knob_colour)
        painter.drawEllipse(QRectF(left, middle - KNOB / 2, KNOB, KNOB))

        if self.text():
            painter.setPen(self._text_colour)
            painter.drawText(
                QRectF(TRACK_W + GAP, 0, self.width() - TRACK_W - GAP, self.height()),
                Qt.AlignVCenter | Qt.AlignLeft,
                self.text(),
            )

    def hitButton(self, point) -> bool:
        return self.rect().contains(point)
