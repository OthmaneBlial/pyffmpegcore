"""
Smoke tests for the root CLI entrypoint.
"""

from __future__ import annotations

import json
import subprocess
import sys

from pyffmpegcore import __version__


def test_cli_root_help_smoke():
    """
    The module entrypoint should print root help and exit cleanly.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "usage: pyffmpegcore" in result.stdout
    assert "--verbose" in result.stdout
    assert "--quiet" in result.stdout


def test_cli_version_smoke():
    """
    The module entrypoint should expose the package version.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == f"pyffmpegcore {__version__}"


def test_cli_rejects_verbose_and_quiet_together():
    """
    Global verbosity flags should remain mutually exclusive.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore", "--verbose", "--quiet"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "not allowed with argument" in result.stderr


def test_global_options_work_before_and_after_subcommands(tmp_path):
    """
    Shared options must not be reset by subparser defaults.
    """
    missing_ffmpeg = str(tmp_path / "missing-ffmpeg")
    before = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "--ffmpeg-path",
            missing_ffmpeg,
            "doctor",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    after = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "doctor",
            "--ffmpeg-path",
            missing_ffmpeg,
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert before.returncode == after.returncode == 3
    assert json.loads(before.stdout)["ffmpeg"]["requested"] == missing_ffmpeg
    assert json.loads(after.stdout)["ffmpeg"]["requested"] == missing_ffmpeg


def test_verbose_is_effective_before_or_after_command():
    """
    Verbose mode should emit stable diagnostic context to stderr.
    """
    for arguments in (("--verbose", "doctor"), ("doctor", "--verbose")):
        result = subprocess.run(
            [sys.executable, "-m", "pyffmpegcore", *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert "[verbose] command=doctor" in result.stderr
        assert "[verbose] ffmpeg=ffmpeg" in result.stderr


def test_incomplete_nested_groups_are_usage_errors():
    """
    Command groups without a nested action must never report success.
    """
    for group in ("speed", "subtitles", "mix-audio", "images"):
        result = subprocess.run(
            [sys.executable, "-m", "pyffmpegcore", group],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 2
        assert "required" in result.stderr


def test_installed_style_smoke_test_json_and_retained_artifacts(tmp_path):
    """
    The smoke command should generate, probe, and retain valid local artifacts.
    """
    artifact_dir = tmp_path / "smoke artifacts"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "smoke-test",
            "--json",
            "--keep-dir",
            str(artifact_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "1.0"
    assert payload["status"] == "ok"
    assert payload["retained"] is True
    assert payload["input"]["video"]["width"] == 320
    assert payload["input"]["video"]["height"] == 180
    assert payload["output"]["image"]["width"] == 160
    assert (artifact_dir / "synthetic-input.mp4").exists()
    assert (artifact_dir / "synthetic-thumbnail.jpg").exists()
