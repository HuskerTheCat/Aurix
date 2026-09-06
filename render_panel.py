"""Render the tray panel to a PNG so its look can be checked."""

import sys

from PySide6.QtWidgets import QApplication

from gab import settings
from gab.panel import Panel

app = QApplication(sys.argv)
settings.load()

panel = Panel(on_pause=lambda _p: None, on_stop_speaking=lambda: None, on_quit=lambda: None)
panel.adjustSize()
panel.grab().save("preview_panel.png")
print("wrote preview_panel.png", panel.width(), "x", panel.height())
