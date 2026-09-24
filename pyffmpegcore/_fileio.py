"""Small filesystem helpers for persistent package state."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TextIO


class DestinationExistsError(FileExistsError):
    """An exclusive write refused to replace the destination itself."""


def atomic_write_text(path: str | Path, content: str) -> Path:
    """Write UTF-8 text through a unique same-directory temporary file."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=".pyffmpegcore-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def exclusive_write_text(path: str | Path, content: str) -> Path:
    """Create UTF-8 text without replacing a path, including on filesystems without hard links."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=".pyffmpegcore-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        try:
            os.link(temporary, destination)
        except FileExistsError as exc:
            raise DestinationExistsError(f"Output already exists: {destination}") from exc
        except OSError:
            try:
                descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError as exc:
                raise DestinationExistsError(f"Output already exists: {destination}") from exc
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(content)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def write_text_file(path: str | Path, content: str, *, overwrite: bool = False) -> Path:
    """Write UTF-8 text atomically, refusing replacement unless explicitly requested."""
    writer = atomic_write_text if overwrite else exclusive_write_text
    return writer(path, content)


def open_text_file(path: str | Path, *, overwrite: bool = False) -> TextIO:
    """Open a UTF-8 output file, claiming a new destination exclusively by default."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if overwrite:
        return destination.open("w", encoding="utf-8")

    try:
        descriptor = os.open(
            destination,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0),
            0o666,
        )
    except FileExistsError as exc:
        raise DestinationExistsError(f"Output already exists: {destination}") from exc
    try:
        return os.fdopen(descriptor, "w", encoding="utf-8")
    except OSError:
        os.close(descriptor)
        raise
