#!/usr/bin/env python3
"""Atheris target for the untrusted pipeline, profile, and receipt parsers."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import atheris

with atheris.instrument_imports():
    from pyffmpegcore.errors import ValidationError
    from pyffmpegcore.pipeline import PipelineSpec
    from pyffmpegcore.profiles import ProfileRegistry
    from pyffmpegcore.receipt import RunReceipt


PARSERS = (PipelineSpec.read, ProfileRegistry().load_file, RunReceipt.read)
MAX_INPUT_BYTES = 8192


def test_one_input(data: bytes) -> None:
    """Send one bounded byte string through one parser boundary."""
    if not data:
        return
    parser = PARSERS[data[0] % len(PARSERS)]
    suffix = (".json", ".json", ".json")[data[0] % len(PARSERS)]
    payload = data[1 : 1 + MAX_INPUT_BYTES]
    with tempfile.NamedTemporaryFile(suffix=suffix) as handle:
        handle.write(payload)
        handle.flush()
        try:
            parser(Path(handle.name))
        except (ValidationError, OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
            return


def main() -> None:
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
