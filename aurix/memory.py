"""What Aurix knows about you, kept between sessions.

Plain text, one note per line, in a file next to settings.json. Plain text on
purpose: the settings window hands you the same file to edit by hand, and
anything structured would mean a parser, and a parser means being wrong about
what you typed.

Nothing is written here unless the model decides an exchange was worth keeping,
and nothing leaves the machine either way.
"""

from . import config, paths


def _file():
    return paths.memory_file()


def text() -> str:
    """The whole thing, exactly as it sits on disk."""
    path = _file()
    if not path.exists():
        return ""
    # utf-8-sig for the same reason settings.json needs it - Notepad puts a
    # byte order mark on anything you save with it, and this file is meant to
    # be edited by hand
    return path.read_text(encoding="utf-8-sig")


def notes() -> list[str]:
    """One note per line, blanks dropped."""
    return [line.strip() for line in text().splitlines() if line.strip()]


def replace(new_text: str) -> None:
    """Write what somebody typed into the settings window, tidied up.

    Trimmed to the same limits the model is held to, so editing by hand cannot
    quietly grow the prompt to the point where it crowds out the question.
    """
    kept = [line.strip() for line in new_text.splitlines() if line.strip()]
    kept = [line[: config.MEMORY_NOTE_CHARS] for line in kept][-config.MEMORY_NOTES :]
    _file().write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")


def clear() -> None:
    replace("")


def remember(fact: str) -> None:
    """Add one note, unless it is already known."""
    fact = fact.strip()[: config.MEMORY_NOTE_CHARS]
    if not fact:
        return

    existing = notes()
    if any(_same(fact, known) for known in existing):
        return
    replace("\n".join(existing + [fact]))


def _same(one: str, other: str) -> bool:
    """Close enough to be the same note.

    Only catches saying the same thing the same way twice, which is what
    actually happens - tell it your name on Monday and again on Friday and the
    model writes the identical line both times. Two different wordings of the
    same fact will both be kept.
    """
    return _bare(one) == _bare(other)


def _bare(line: str) -> str:
    return "".join(letter for letter in line.lower() if letter.isalnum() or letter == " ").strip()


def for_prompt() -> str:
    """The block that goes into the system prompt, or nothing at all."""
    known = notes()
    if not known:
        return ""
    listed = "\n".join(f"- {note}" for note in known)
    return config.MEMORY_PROMPT.format(notes=listed)
