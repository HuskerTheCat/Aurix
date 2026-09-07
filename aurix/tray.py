"""The system tray icon."""

import pystray
from PIL import Image, ImageDraw


def _icon_image() -> Image.Image:
    """A blue dot, until there is a real icon."""
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((6, 6, size - 6, size - 6), fill=(70, 120, 240, 255))
    draw.ellipse((20, 18, size - 28, size - 30), fill=(200, 220, 255, 255))
    return image


def create(on_open, on_quit) -> pystray.Icon:
    """on_open runs on a left click; on_quit is passed the icon."""
    menu = pystray.Menu(
        pystray.MenuItem("Open Aurix", lambda _icon, _item: on_open(), default=True),
        pystray.MenuItem("Quit Aurix", lambda icon, _item: on_quit(icon)),
    )
    return pystray.Icon("aurix", _icon_image(), "Aurix", menu)
