"""Validate the real terminal recording and derive its accessible transcript."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ANSI_ESCAPE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
PRIVATE_PATHS = ("/Users/", "/home/", "C:\\Users\\")


def read_cast(path: Path) -> tuple[dict[str, object], list[list[object]]]:
    """Read an asciicast v2 file with strict line-level JSON validation."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        raise ValueError("recording must contain a header and output events")
    header = json.loads(lines[0])
    events = [json.loads(line) for line in lines[1:]]
    if not isinstance(header, dict) or header.get("version") != 2:
        raise ValueError("recording must use asciicast v2")
    if not all(
        isinstance(event, list)
        and len(event) == 3
        and isinstance(event[0], (int, float))
        and isinstance(event[1], str)
        and event[1] in {"i", "o"}
        and isinstance(event[2], str)
        for event in events
    ):
        raise ValueError("recording contains an invalid event")
    return header, events


def plain_output(events: list[list[object]]) -> str:
    """Collapse output events into readable terminal text."""
    raw = "".join(str(event[2]) for event in events if event[1] == "o")
    return ANSI_ESCAPE.sub("", raw).replace("\r", "\n")


def validate_recording(path: Path, *, expected_version: str) -> tuple[float, str]:
    """Enforce duration, privacy, and end-to-end content requirements."""
    _, events = read_cast(path)
    timestamp = events[-1][0]
    if not isinstance(timestamp, (int, float)):  # narrowed again for static type checkers
        raise ValueError("recording ends with an invalid timestamp")
    duration = float(timestamp)
    transcript = plain_output(events)

    if not 60 <= duration <= 90:
        raise ValueError(f"terminal demo must last 60–90 seconds; recorded {duration:.1f}s")
    required = (
        f"pip install pyffmpegcore=={expected_version}",
        f"pyffmpegcore {expected_version}",
        "ffmpeg: OK",
        "Smoke test: PASS",
        "Plan 1.0",
        "Progress:",
        "Output:",
        "Receipt:",
        "Valid receipt: schema 1.0",
        "No upload. No telemetry.",
    )
    missing = [snippet for snippet in required if snippet not in transcript]
    if missing:
        raise ValueError(f"terminal demo is missing required real output: {missing!r}")
    leaked = [prefix for prefix in PRIVATE_PATHS if prefix in transcript]
    if leaked:
        raise ValueError(f"terminal demo exposes a private home path: {leaked!r}")
    return duration, transcript


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cast", type=Path, required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--transcript", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        duration, transcript = validate_recording(
            args.cast,
            expected_version=args.expected_version.removeprefix("v"),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.transcript.write_text(transcript, encoding="utf-8")
    print(f"Validated real terminal demo: {duration:.1f}s; transcript={args.transcript}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
