"""
Tests for the CLI doctor command.
"""

from __future__ import annotations

import json
import subprocess
import sys


def test_doctor_json_smoke():
    """
    The doctor command should return JSON diagnostics for the current environment.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore", "doctor", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["cli_version"]
    assert payload["platform"]["system"]
    assert payload["python"]["version"]
    assert payload["ffmpeg"]["available"] is True
    assert payload["ffprobe"]["available"] is True


def test_doctor_reports_missing_binary_with_environment_exit_code():
    """
    Missing binaries should be reported clearly and return the environment error code.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "doctor",
            "--json",
            "--ffmpeg-path",
            "/definitely/missing/ffmpeg",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 3
    payload = json.loads(result.stdout)
    assert payload["ffmpeg"]["available"] is False
    assert "Executable not found" in payload["ffmpeg"]["error"]
