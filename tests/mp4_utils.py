"""
Helpers for inspecting MP4 container structure in tests.
"""

from __future__ import annotations

import struct
from pathlib import Path


def top_level_mp4_atoms(path: Path) -> list[str]:
    atoms = []
    with path.open("rb") as handle:
        while True:
            header = handle.read(8)
            if len(header) < 8:
                break

            size, atom_type = struct.unpack(">I4s", header)
            atom_name = atom_type.decode("ascii", errors="replace")
            atoms.append(atom_name)

            if size == 0:
                break
            if size == 1:
                largesize = handle.read(8)
                if len(largesize) < 8:
                    break
                size = struct.unpack(">Q", largesize)[0]
                handle.seek(size - 16, 1)
            else:
                handle.seek(size - 8, 1)

    return atoms
