#!/usr/bin/env python3
"""
Generate and verify deterministic, redistribution-safe media fixtures.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST = SCRIPT_DIR / "manifest.json"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "downloads"


def probe_media(path: Path, ffprobe_path: str) -> dict:
    result = subprocess.run(
        [
            ffprobe_path,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Unable to probe {path}")
    return json.loads(result.stdout)


def validate_fixture(path: Path, fixture: dict, ffprobe_path: str) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"Fixture is missing or empty: {path}")

    generator = fixture["generator"]
    if generator["type"] == "text":
        actual = path.read_text(encoding="utf-8")
        if actual != generator["content"]:
            raise RuntimeError(f"Text fixture content mismatch: {path.name}")
        return

    metadata = probe_media(path, ffprobe_path)
    validation = fixture.get("validation", {})
    streams = metadata.get("streams", [])

    format_contains = validation.get("format_contains")
    format_name = metadata.get("format", {}).get("format_name", "")
    if format_contains and format_contains not in format_name:
        raise RuntimeError(f"Unexpected format for {path.name}: expected {format_contains!r} in {format_name!r}")

    for stream_type in ("video", "audio"):
        expected_codec = validation.get(f"{stream_type}_codec")
        if not expected_codec:
            continue
        candidates = [stream for stream in streams if stream.get("codec_type") == stream_type]
        if not candidates:
            raise RuntimeError(f"Missing {stream_type} stream in {path.name}")
        actual_codec = candidates[0].get("codec_name")
        if actual_codec != expected_codec:
            raise RuntimeError(
                f"Unexpected {stream_type} codec for {path.name}: expected {expected_codec}, got {actual_codec}"
            )

    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    if video_streams:
        video = video_streams[0]
        for dimension in ("width", "height"):
            expected = validation.get(dimension)
            if expected is not None and video.get(dimension) != expected:
                raise RuntimeError(
                    f"Unexpected {dimension} for {path.name}: expected {expected}, got {video.get(dimension)}"
                )

    minimum_duration = validation.get("minimum_duration")
    if minimum_duration is not None:
        duration_text = metadata.get("format", {}).get("duration")
        duration = float(duration_text or 0)
        if duration < float(minimum_duration):
            raise RuntimeError(
                f"Fixture {path.name} is too short: expected at least {minimum_duration}s, got {duration}s"
            )


def generate_fixture(
    output_dir: Path,
    fixture: dict,
    *,
    ffmpeg_path: str,
    ffprobe_path: str,
    force: bool,
) -> None:
    destination = output_dir / fixture["filename"]
    if destination.exists() and not force:
        try:
            validate_fixture(destination, fixture, ffprobe_path)
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            print(f"[stale] {destination.name}: {exc}")
        else:
            print(f"[ok] {destination.name} already verified")
            return

    output_dir.mkdir(parents=True, exist_ok=True)
    generator = fixture["generator"]
    with tempfile.NamedTemporaryFile(
        dir=output_dir,
        prefix=f".{destination.stem}-",
        suffix=destination.suffix,
        delete=False,
    ) as temp_handle:
        temp_path = Path(temp_handle.name)

    try:
        if generator["type"] == "text":
            temp_path.write_text(generator["content"], encoding="utf-8")
        elif generator["type"] == "ffmpeg":
            command = [
                ffmpeg_path,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                *[str(temp_path) if token == "{output}" else token for token in generator["args"]],
            ]
            print(f"[generate] {destination.name}")
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or f"FFmpeg failed to generate {destination.name}")
        else:
            raise RuntimeError(f"Unsupported generator type: {generator['type']}")

        validate_fixture(temp_path, fixture, ffprobe_path)
        temp_path.replace(destination)
        print(f"[verified] {destination.name}")
    finally:
        temp_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--ffmpeg-path", default="ffmpeg")
    parser.add_argument("--ffprobe-path", default="ffprobe")
    parser.add_argument("--force", action="store_true", help="regenerate every fixture")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    fixtures = manifest.get("fixtures", [])
    if not fixtures:
        raise RuntimeError(f"No fixtures defined in {args.manifest}")

    for fixture in fixtures:
        generate_fixture(
            args.output_dir,
            fixture,
            ffmpeg_path=args.ffmpeg_path,
            ffprobe_path=args.ffprobe_path,
            force=args.force,
        )

    print(f"Generated and verified {len(fixtures)} fixtures in {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
