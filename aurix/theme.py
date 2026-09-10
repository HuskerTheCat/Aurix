"""Colour schemes for the panel and the settings window."""

from . import settings

THEMES = {
    "midnight": {
        "name": "Midnight",
        "bg": "#14151c", "surface": "#1e2029", "border": "#2f3345",
        "text": "#c9cfe0", "bright": "#eef1f8",
        "accent": "#5a8cff", "soft": "#1b2540",
    },
    "slate": {
        "name": "Slate",
        "bg": "#16181a", "surface": "#212427", "border": "#34383d",
        "text": "#c8ced4", "bright": "#eef1f4",
        "accent": "#7f9cc4", "soft": "#1e242c",
    },
    "forest": {
        "name": "Forest",
        "bg": "#101613", "surface": "#1a221d", "border": "#2c3a31",
        "text": "#c2d2c7", "bright": "#e9f3ec",
        "accent": "#4fbf8b", "soft": "#16291f",
    },
    "plum": {
        "name": "Plum",
        "bg": "#17131c", "surface": "#221c29", "border": "#382f43",
        "text": "#cfc6d8", "bright": "#f1ecf6",
        "accent": "#b07cff", "soft": "#251a33",
    },
    "light": {
        "name": "Light",
        "bg": "#f4f5f8", "surface": "#ffffff", "border": "#d5d9e2",
        "text": "#3a4050", "bright": "#171a21",
        "accent": "#3a6df0", "soft": "#e6ecfb",
    },
}

TEMPLATE = """
QWidget {{ background: {bg}; color: {text}; font-family: 'Segoe UI'; font-size: 12px; }}
QWidget#panel {{ border: 1px solid {border}; border-radius: 12px; }}
/* the settings window draws its own frame, so Windows does not paint a
   red title bar over the top of it */
QWidget#settings {{ background: transparent; }}
QFrame#shell {{
    background: {bg}; border: 1px solid {border}; border-radius: 12px;
}}
/* padding: 0 matters. Without it this inherits the 6px 12px above, which
   makes the button want to be 39x32, and the fixed 28x28 then crops the
   glyph - worse the higher your display scaling is. */
QPushButton#close {{
    background: transparent; border: none; color: {text}; font-size: 15px;
    padding: 0;
}}
QPushButton#close:hover {{ background: {surface}; border-radius: 6px; color: {bright}; }}
QLabel {{ background: transparent; }}
QLabel#title {{ color: {bright}; font-size: 15px; font-weight: 600; }}
QLabel#heading {{ color: {bright}; font-size: 13px; font-weight: 600; }}
QLabel#dim {{ color: {text}; font-size: 11px; }}
QLabel#wakeword {{
    background: {soft}; color: {accent}; border: 1px solid {border};
    border-radius: 6px; padding: 7px 10px; font-size: 13px;
}}
QComboBox, QLineEdit, QPlainTextEdit {{
    background: {surface}; color: {bright}; border: 1px solid {border};
    border-radius: 6px; padding: 5px 8px;
}}
/* the memory notes are meant to be read and edited a line at a time, so they
   get a little more room than the 12px everything else uses */
QPlainTextEdit {{ font-size: 13px; }}
QComboBox QAbstractItemView {{
    background: {surface}; color: {bright}; selection-background-color: {accent};
}}
QCheckBox, QRadioButton {{ background: transparent; }}
QPushButton {{
    background: {surface}; color: {bright}; border: 1px solid {border};
    border-radius: 6px; padding: 6px 12px;
}}
QPushButton:hover {{ border-color: {accent}; }}
QPushButton:disabled {{ color: {border}; }}
QPushButton#primary {{ background: {accent}; color: {bg}; border-color: {accent}; }}
QPushButton#quit {{ color: #e07a7a; }}
QSlider::groove:horizontal {{ height: 4px; background: {border}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {accent}; width: 13px; height: 13px; margin: -5px 0; border-radius: 6px;
}}
QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 2px; }}
QTabWidget::pane {{ border: 1px solid {border}; border-radius: 8px; top: -1px; }}
QTabBar::tab {{
    background: transparent; color: {text}; padding: 8px 16px;
    border: 1px solid transparent; border-bottom: none;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
}}
QTabBar::tab:selected {{ color: {bright}; background: {surface}; border-color: {border}; }}
QFrame#card {{
    background: {surface}; border: 1px solid {border}; border-radius: 8px;
}}
QFrame#card[chosen="true"] {{ border: 1px solid {accent}; background: {soft}; }}
QProgressBar {{
    background: {bg}; border: 1px solid {border}; border-radius: 5px;
    height: 10px; text-align: center; color: {text};
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 4px; }}
QScrollArea {{ border: none; }}
"""


def palette() -> dict:
    return THEMES[settings.get("theme")]


def stylesheet() -> str:
    return TEMPLATE.format(**palette())


def switch_colours() -> tuple:
    """The switch paints itself, so it cannot pick these up from the stylesheet."""
    colours = palette()
    return colours["accent"], colours["border"], colours["bright"], colours["text"]
