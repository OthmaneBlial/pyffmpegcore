"""
Tests for stable CLI error categories and exit codes.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

import pytest

from pyffmpegcore.cli import main
from pyffmpegcore.cli_common import echo_error


def test_echo_error_preserves_lines_only_for_structured_reports(capsys):
    echo_error("untrusted\nline")
    assert capsys.readouterr().err == "untrusted\\nline\n"

    echo_error("Preflight FAIL\n[FAIL] output: collision\n  Remedy: choose another path", preserve_newlines=True)
    assert capsys.readouterr().err == "Preflight FAIL\n[FAIL] output: collision\n  Remedy: choose another path\n"


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
    assert "--ffprobe-path" in result.stderr


def test_cli_probe_reports_malformed_ffprobe_json_as_runtime_error(tmp_path, monkeypatch, capsys):
    input_file = tmp_path / "movie.mkv"
    input_file.write_bytes(b"fixture")
    monkeypatch.setattr(
        "pyffmpegcore.probe.subprocess.run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "{truncated", ""),
    )

    result = main(["probe", "--input", str(input_file)])

    assert result == 5
    assert "FFprobe returned an invalid JSON document" in capsys.readouterr().err


def test_probe_rejects_remote_url_without_echoing_credentials():
    secret = "https://user:do-not-log@example.invalid/media.mp4?token=do-not-log"
    result = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore", "probe", "--input", secret],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 4
    assert "local file" in result.stderr
    assert "do-not-log" not in result.stdout + result.stderr


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


@pytest.mark.parametrize("option", ["--target-size", "--min-video-bitrate"])
def test_compress_reports_numeric_overflow_as_validation_error(tmp_path, capsys, option):
    input_file = tmp_path / "input.mp4"
    input_file.write_bytes(b"fixture")

    result = main(["compress", "--input", str(input_file), "--output", str(tmp_path / "output.mp4"), option, "9" * 400])

    assert result == 4
    assert "signed 64-bit FFmpeg value" in capsys.readouterr().err


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
