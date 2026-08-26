"""
Tests for stable CLI error categories and exit codes.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

import pytest

from pyffmpegcore.cli import main


def test_cli_missing_input_returns_validation_error(tmp_path):
    """
    Missing inputs should return the validation exit code.
    """
    missing = tmp_path / "missing.mp4"
    result = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore", "probe", "--input", str(missing)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 4
    assert "Input path does not exist" in result.stderr


def test_cli_missing_binary_returns_environment_error(tmp_path):
    """
    Missing FFprobe binaries should return the environment exit code.
    """
    existing = tmp_path / "existing.mp4"
    existing.write_text("placeholder", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "probe",
            "--input",
            str(existing),
            "--ffprobe-path",
            "/definitely/missing/ffprobe",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 3


def test_cli_missing_required_stream_returns_validation_error(tmp_path):
    """
    Capability-aware preflight should reject a missing required stream before execution.
    """
    input_file = tmp_path / "plain.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x120:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(input_file),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "subtitles",
            "extract",
            "--video",
            str(input_file),
            "--output",
            str(tmp_path / "subs.srt"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 4
    assert "Missing required streams: subtitle" in result.stderr


@pytest.mark.parametrize(
    "arguments",
    [
        ["compress", "--crf", "99"],
        ["thumbnail", "--width", "0"],
        ["waveform", "--width", "0"],
    ],
)
def test_planner_value_errors_return_validation_category(tmp_path, arguments):
    """Typed option validation failures must remain category 4, not processing failures."""
    input_file = tmp_path / "input.mp4"
    output_file = tmp_path / "output.mp4"
    input_file.write_bytes(b"fixture")

    argv = [*arguments, "--input", str(input_file), "--output", str(output_file)]

    assert main(argv) == 4


def test_preserve_all_streams_rejects_explicit_pixel_format(tmp_path, capsys):
    input_file = tmp_path / "input.mkv"
    input_file.write_bytes(b"fixture")

    returncode = main(
        [
            "convert",
            "--input",
            str(input_file),
            "--output",
            str(tmp_path / "output.mkv"),
            "--preserve-all-streams",
            "--pix-fmt",
            "yuv420p",
        ]
    )

    assert returncode == 4
    assert "cannot be combined with --pix-fmt" in capsys.readouterr().err


@pytest.mark.real_media
def test_cli_partial_success_exit_code_for_images(tmp_path):
    """
    Batch image commands should return the partial-success exit code when some files fail.
    """
    from tests.media_utils import ensure_downloaded_media

    media = ensure_downloaded_media()
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    (input_dir / "broken.png").write_text("broken", encoding="utf-8")
    shutil.copy2(media["image_png"], input_dir / "good.png")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "images",
            "convert",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--format",
            "jpg",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 6
