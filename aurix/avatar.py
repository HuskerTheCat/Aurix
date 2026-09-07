"""The face Aurix wears on screen.

A placeholder protogen drawn in code, so the whole thing is built and working
before any art exists. Everything here is one function taking a painter and a
box, so swapping in real artwork later means replacing this file and nothing
else.
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen, QRadialGradient

# The face is drawn into a box this size and scaled, so all the numbers below
# are in one fixed coordinate space rather than relative to the window.
WIDTH = 132.0
HEIGHT = 108.0

SHELL = QColor(38, 40, 52)
SHELL_EDGE = QColor(70, 74, 94)
VISOR = QColor(14, 15, 22)

# Same states as the orb, so nothing else had to change.
COLOURS = {
    "starting": (150, 160, 200),
    "listening": (90, 170, 255),
    "thinking": (165, 120, 255),
    "searching": (255, 180, 80),
    "done": (95, 215, 165),
}


def paint(painter, centre: QPointF, scale: float, state: str, level: float,
          phase: float) -> None:
    """Draw the face centred on a point.

    level is 0 to 1 - the microphone while listening, the voice while talking.
    phase just keeps counting up, for anything that moves on its own.
    """
    glow = QColor(*COLOURS.get(state, COLOURS["listening"]))
    breath = 0.5 + 0.5 * math.sin(phase * 1.6)
    loud = min(level * 9.0, 1.0)

    painter.save()
    painter.translate(centre)
    painter.scale(scale, scale)
    # a slow bob, and a bigger one when there is sound
    painter.translate(0.0, -2.0 * breath - 3.0 * loud)

    _ears(painter, glow, state, breath, loud)
    _head(painter)
    _visor(painter, glow)
    _jaw(painter, glow)
    _face(painter, glow, state, loud, phase)

    painter.restore()


def _head(painter) -> None:
    """The shell: angular, wider at the top, tapering to a flat jaw."""
    path = QPainterPath()
    path.moveTo(-54, -30)
    path.lineTo(-44, -40)
    path.lineTo(44, -40)
    path.lineTo(54, -30)
    path.lineTo(50, 12)
    path.lineTo(34, 34)
    path.lineTo(-34, 34)
    path.lineTo(-50, 12)
    path.closeSubpath()

    painter.setBrush(SHELL)
    painter.setPen(QPen(SHELL_EDGE, 2.0))
    painter.drawPath(path)


def _jaw(painter, glow: QColor) -> None:
    """A lit strip under the visor, so the face is not floating on a blank chin."""
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(glow.red(), glow.green(), glow.blue(), 60))
    painter.drawRoundedRect(QRectF(-20, 20, 40, 7), 3, 3)


def _ears(painter, glow: QColor, state: str, breath: float, loud: float) -> None:
    """Chunky angular ears. They perk up when listening and droop when idle."""
    perk = {
        "starting": -12.0,
        "listening": 10.0 + 5.0 * loud,
        "thinking": 2.0,
        "searching": 5.0,
        "done": 8.0,
    }.get(state, 0.0) + 1.5 * breath

    for side in (-1, 1):
        painter.save()
        painter.translate(side * 40, -32)
        painter.rotate(side * (18 - perk))

        ear = QPainterPath()
        ear.moveTo(-16, 6)
        ear.lineTo(-8, -36)
        ear.lineTo(4, -32)
        ear.lineTo(16, 4)
        ear.closeSubpath()
        painter.setBrush(SHELL)
        painter.setPen(QPen(SHELL_EDGE, 2.0))
        painter.drawPath(ear)

        inner = QPainterPath()
        inner.moveTo(-8, 0)
        inner.lineTo(-4, -25)
        inner.lineTo(2, -23)
        inner.lineTo(8, -1)
        inner.closeSubpath()
        painter.setBrush(QColor(glow.red(), glow.green(), glow.blue(), 140))
        painter.setPen(Qt.NoPen)
        painter.drawPath(inner)

        painter.restore()


def _visor(painter, glow: QColor) -> None:
    """The screen the whole face happens on. Chamfered, like a real one."""
    screen = QPainterPath()
    screen.moveTo(-46, -26)
    screen.lineTo(46, -26)
    screen.lineTo(46, 2)
    screen.lineTo(30, 16)
    screen.lineTo(-30, 16)
    screen.lineTo(-46, 2)
    screen.closeSubpath()

    halo = QRadialGradient(QPointF(0, -6), 80)
    halo.setColorAt(0.0, QColor(glow.red(), glow.green(), glow.blue(), 76))
    halo.setColorAt(1.0, QColor(glow.red(), glow.green(), glow.blue(), 0))
    painter.setPen(Qt.NoPen)
    painter.setBrush(halo)
    painter.drawEllipse(QPointF(0, -6), 80, 80)

    painter.setBrush(VISOR)
    painter.setPen(QPen(QColor(glow.red(), glow.green(), glow.blue(), 200), 2.4))
    painter.drawPath(screen)


def _face(painter, glow: QColor, state: str, loud: float, phase: float) -> None:
    """Eyes and mouth, lit up on the visor."""
    painter.setPen(QPen(glow, 5.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(Qt.NoBrush)

    for side in (-1, 1):
        painter.save()
        painter.translate(side * 22, -10)
        painter.scale(side, 1)
        _eye(painter, glow, state, side, phase)
        painter.restore()

    _mouth(painter, glow, state, loud)


def _eye(painter, glow: QColor, state: str, side: int, phase: float) -> None:
    if state == "starting":  # half asleep
        painter.drawLine(QPointF(-9, 0), QPointF(9, 0))
        return

    if state == "thinking":  # screwed up in concentration, > <
        painter.drawLine(QPointF(9, -5), QPointF(-9, 0))
        painter.drawLine(QPointF(-9, 0), QPointF(9, 5))
        return

    if state == "searching":  # eyes flicking about
        painter.translate(4.0 * math.sin(phase * 3.0), 0)
        painter.setBrush(glow)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(0, 0), 5.5, 5.5)
        return

    if state == "done":  # a happy ^ ^
        painter.drawLine(QPointF(-9, 3), QPointF(0, -5))
        painter.drawLine(QPointF(0, -5), QPointF(9, 3))
        return

    painter.setBrush(glow)  # listening: wide awake
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(QPointF(0, 0), 8.0, 8.0)
    painter.setBrush(QColor(255, 255, 255, 170))
    painter.drawEllipse(QPointF(-2.4, -2.4), 2.6, 2.6)


def _mouth(painter, glow: QColor, state: str, loud: float) -> None:
    """Opens with whatever it is saying, so it looks like it is talking."""
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(glow.red(), glow.green(), glow.blue(), 220))

    if state == "starting":
        return

    open_by = 2.0 + 12.0 * loud
    painter.drawRoundedRect(QRectF(-10, 4, 20, open_by), 4, 4)
