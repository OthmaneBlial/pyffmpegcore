"""
Tests for stable CLI error categories and exit codes.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

import pytest


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


def test_cli_processing_failure_returns_runtime_error(tmp_path):
    """
    FFmpeg processing failures should return the runtime exit code.
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

    assert result.returncode == 5


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
