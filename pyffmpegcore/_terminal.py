"""Helpers for rendering untrusted text safely in a terminal."""

from __future__ import annotations


def terminal_safe_text(value: object, *, preserve_newlines: bool = False) -> str:
    """Escape terminal control and formatting characters as visible text."""
    escaped: list[str] = []
    for character in str(value):
        if preserve_newlines and character == "\n":
            escaped.append(character)
        elif character.isprintable() or character in {"\u200c", "\u200d"}:
            escaped.append(character)
        else:
            escaped.append(character.encode("unicode_escape").decode("ascii"))
    return "".join(escaped)
