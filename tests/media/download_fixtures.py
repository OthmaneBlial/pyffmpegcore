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
            "-show_chapters",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
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

    expected_counts = validation.get("stream_counts", {})
    for stream_type, expected_count in expected_counts.items():
        actual_count = sum(stream.get("codec_type") == stream_type for stream in streams)
        if actual_count != expected_count:
            raise RuntimeError(
                f"Unexpected {stream_type} stream count for {path.name}: expected {expected_count}, got {actual_count}"
            )

    actual_format_tags = {key.casefold(): value for key, value in metadata.get("format", {}).get("tags", {}).items()}
    for key, expected_value in validation.get("format_tags", {}).items():
        if actual_format_tags.get(key.casefold()) != expected_value:
            raise RuntimeError(
                f"Unexpected format tag {key!r} for {path.name}: "
                f"expected {expected_value!r}, got {actual_format_tags.get(key.casefold())!r}"
            )

    for stream_type, expected_languages in validation.get("stream_languages", {}).items():
        actual_languages = [
            stream.get("tags", {}).get("language") for stream in streams if stream.get("codec_type") == stream_type
        ]
        if actual_languages != expected_languages:
            raise RuntimeError(
                f"Unexpected {stream_type} languages for {path.name}: "
                f"expected {expected_languages!r}, got {actual_languages!r}"
            )

    expected_chapters = validation.get("chapter_titles")
    if expected_chapters is not None:
        actual_chapters = [chapter.get("tags", {}).get("title") for chapter in metadata.get("chapters", [])]
        if actual_chapters != expected_chapters:
            raise RuntimeError(
                f"Unexpected chapter titles for {path.name}: expected {expected_chapters!r}, got {actual_chapters!r}"
            )

    if validation.get("attached_picture"):
        attached = [
            stream
            for stream in streams
            if stream.get("codec_type") == "video" and stream.get("disposition", {}).get("attached_pic") == 1
        ]
        if not attached:
            raise RuntimeError(f"Missing attached cover-art stream in {path.name}")

    expected_rotation = validation.get("rotation")
    if expected_rotation is not None:
        rotations = []
        for stream in video_streams:
            tag_rotation = stream.get("tags", {}).get("rotate")
            if tag_rotation is not None:
                rotations.append(float(tag_rotation))
            rotations.extend(
                float(item["rotation"]) for item in stream.get("side_data_list", []) if item.get("rotation") is not None
            )
        if float(expected_rotation) not in rotations:
            raise RuntimeError(f"Missing rotation {expected_rotation} in {path.name}: got {rotations!r}")

    if validation.get("variable_frame_rate"):
        if not video_streams:
            raise RuntimeError(f"Missing video stream for VFR validation in {path.name}")
        video = video_streams[0]
        if video.get("r_frame_rate") == video.get("avg_frame_rate"):
            raise RuntimeError(f"Fixture {path.name} does not expose distinct nominal and average frame rates")


def expand_generator_args(args: list[str], output_dir: Path, output_path: Path) -> list[str]:
    """Resolve safe fixture references and the current output placeholder."""
    expanded = []
    for token in args:
        if token == "{output}":
            expanded.append(str(output_path))
            continue
        if token.startswith("{fixture:") and token.endswith("}"):
            filename = token[len("{fixture:") : -1]
            if not filename or Path(filename).name != filename:
                raise RuntimeError(f"Unsafe fixture reference: {token}")
            fixture_path = output_dir / filename
            if not fixture_path.exists():
                raise RuntimeError(f"Referenced fixture has not been generated yet: {filename}")
            expanded.append(str(fixture_path))
            continue
        expanded.append(token)
    return expanded


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
                *expand_generator_args(generator["args"], output_dir, temp_path),
            ]
            print(f"[generate] {destination.name}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
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
