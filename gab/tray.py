"""The system tray icon - the only thing visible when Gab is idle."""

import pystray
from PIL import Image, ImageDraw


def _icon_image() -> Image.Image:
    """A simple blue dot. Placeholder until the real icon is designed."""
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((6, 6, size - 6, size - 6), fill=(70, 120, 240, 255))
    draw.ellipse((20, 18, size - 28, size - 30), fill=(200, 220, 255, 255))
    return image


def create(on_quit) -> pystray.Icon:
    """Build the tray icon. on_quit is called with the icon when Quit is picked."""
    menu = pystray.Menu(pystray.MenuItem("Quit Gab", lambda icon, _item: on_quit(icon)))
    return pystray.Icon("gab", _icon_image(), "Gab", menu)
