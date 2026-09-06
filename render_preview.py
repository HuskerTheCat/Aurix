"""Render the orb to PNG files so its look can be checked without staring at a screen."""

import sys

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QLinearGradient
from PySide6.QtWidgets import QApplication

from gab.overlay import HEIGHT, WIDTH, Overlay

app = QApplication(sys.argv)
overlay = Overlay()

STATES = [
    ("listening_quiet", "listening", 0.0, 0.0),
    ("listening_loud", "listening", 0.08, 1.2),
    ("thinking", "thinking", 0.0, 2.4),
    ("done", "done", 0.0, 3.1),
]

CAPTIONS = {
    "listening": "Listening",
    "thinking": "Thinking",
    "done": "How long does it take to drive to Denver?",
}

for name, state, level, phase in STATES:
    overlay._state = state
    overlay._caption = CAPTIONS[state]
    overlay._level = level
    overlay._eased_level = level
    overlay._phase = phase

    # a desktop-ish background, so transparency and contrast are visible
    image = QImage(WIDTH, HEIGHT, QImage.Format_ARGB32_Premultiplied)
    painter = QPainter(image)
    backdrop = QLinearGradient(QPointF(0, 0), QPointF(WIDTH, HEIGHT))
    backdrop.setColorAt(0.0, QColor(58, 78, 112))
    backdrop.setColorAt(1.0, QColor(122, 96, 76))
    painter.fillRect(image.rect(), backdrop)
    painter.end()

    overlay.render(image, QPointF(0, 0).toPoint())
    image.save(f"preview_{name}.png")
    print(f"wrote preview_{name}.png")

print("done")
