"""Starting programs that are already installed.

The model never names an executable. It names a program the way a person would,
and that has to match a shortcut in the Start Menu - so the only things Aurix
can start are things already installed, and opening one is the same as clicking
it yourself. There is no path anywhere the model can reach.

The system tool folders are left out on purpose. A misheard sentence should not
be able to reach the registry editor.
"""

import os
import re
from pathlib import Path

_START_MENUS = (
    r"%ProgramData%\Microsoft\Windows\Start Menu\Programs",
    r"%APPDATA%\Microsoft\Windows\Start Menu\Programs",
)

# Nobody means these by "open something", and some of them are worth not reaching.
_SKIP_FOLDERS = {
    "administrative tools", "windows administrative tools", "windows tools",
    "windows system", "windows powershell", "system tools", "startup",
    "accessibility",
}

# Shortcuts that sit beside a program without being it.
_NOT_PROGRAMS = (
    "uninstall", "readme", "read me", "documentation", "help", "release notes",
    "website", "home page", "homepage", "manual", "changelog", "support",
    "license", "licence",
)

# Real programs, but not ones a misheard sentence should ever open. Installers
# drop shells well outside the system folders - "Node.js command prompt", "Git
# CMD", "Developer PowerShell for VS" - so skipping those folders does not catch
# them and the name has to.
_NEVER = (
    "command prompt", "powershell", "cmd", "terminal", "console", "shell",
    "bash", "registry", "regedit", "control panel", "task manager",
    "event viewer", "device manager", "services",
)

_installed: dict[str, Path] | None = None


def launch(spoken: str) -> str:
    """Open a program by name. Returns what to say back."""
    shortcut = _find(spoken)
    if shortcut is None:
        return f"I do not have a program called {spoken}."
    os.startfile(str(shortcut))
    return f"Opening {shortcut.stem}."


def _find(spoken: str):
    """The program somebody means, or None when nothing installed matches.

    An exact name wins outright. Otherwise the whole of what was said has to
    appear in a name as whole words, because people say "Chrome" and the
    shortcut is called "Google Chrome". The shortest of those is the plain one -
    "VLC media player" rather than "VLC media player skinned".

    Whole words is what keeps it honest: "word" does not reach WordPad. Nothing
    partial ever matches, since guessing is how a misheard sentence starts
    something nobody asked for.
    """
    wanted = _plainly(spoken)
    if not wanted:
        return None

    installed = _all_of_them()
    if wanted in installed:
        return installed[wanted]

    within = [name for name in installed if f" {wanted} " in f" {name} "]
    if not within:
        return None
    return installed[min(within, key=len)]


def _all_of_them() -> dict[str, Path]:
    """Every program in the Start Menu, by the name a person would say.

    Read once. Installing something while Aurix is running means restarting it,
    which is a fair trade for not walking the disk on every request.
    """
    global _installed
    if _installed is not None:
        return _installed

    _installed = {}
    for folder in _START_MENUS:
        root = Path(os.path.expandvars(folder))
        if not root.is_dir():
            continue
        for shortcut in root.rglob("*.lnk"):
            if _in_a_skipped_folder(shortcut.relative_to(root)):
                continue
            name = _plainly(shortcut.stem)
            if name and _worth_opening(name):
                _installed.setdefault(name, shortcut)
    return _installed


def _in_a_skipped_folder(relative: Path) -> bool:
    return any(_plainly(part) in _SKIP_FOLDERS for part in relative.parts[:-1])


def _worth_opening(name: str) -> bool:
    """Whole words, so "Helper" survives and "Discord Uninstall" does not."""
    padded = f" {name} "
    return not any(f" {phrase} " in padded for phrase in _NOT_PROGRAMS + _NEVER)


def _plainly(name: str) -> str:
    """A name as it would be said: no case, no punctuation, no double spaces."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", name.lower())).strip()
