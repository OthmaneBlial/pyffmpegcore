"""Small filesystem helpers for persistent package state."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


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
        except FileExistsError:
            raise
        except OSError:
            descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(content)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination
