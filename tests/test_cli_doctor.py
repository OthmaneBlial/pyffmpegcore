"""
Tests for the CLI doctor command.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from unittest.mock import patch

from pyffmpegcore.cli import CLIContext, collect_doctor_report, handle_doctor, inspect_binary, render_doctor_report


@patch("pyffmpegcore.cli.shutil.which", return_value="/usr/bin/ffmpeg")
@patch("pyffmpegcore.cli.subprocess.run")
def test_binary_inspection_decodes_tool_output_as_utf8(mock_run, _mock_which):
    mock_run.return_value = subprocess.CompletedProcess(["ffmpeg", "-version"], 0, "ffmpeg version 9.0\n", "")

    assert inspect_binary("ffmpeg")["version"] == "ffmpeg version 9.0"
    assert mock_run.call_args.kwargs["encoding"] == "utf-8"
    assert mock_run.call_args.kwargs["errors"] == "replace"
    assert mock_run.call_args.kwargs["timeout"] == 5


@patch("pyffmpegcore.cli.shutil.which", return_value="/usr/bin/ffmpeg")
@patch("pyffmpegcore.cli.subprocess.run", side_effect=subprocess.TimeoutExpired(["ffmpeg", "-version"], 5))
def test_binary_inspection_reports_a_timed_out_version_probe(mock_run, _mock_which):
    report = inspect_binary("ffmpeg")

    assert report["available"] is False
    assert report["error"] == "Version probe timed out after 5 seconds."
    assert mock_run.call_args.kwargs["timeout"] == 5


@patch("pyffmpegcore.cli.inspect_ffmpeg_capabilities", side_effect=RuntimeError("listing timed out"))
@patch(
    "pyffmpegcore.cli.inspect_binary",
    return_value={"available": True, "resolved": "/usr/bin/ffmpeg", "version": "ffmpeg 9", "error": None},
)
def test_doctor_reports_capability_listing_failure(_mock_inspect_binary, _mock_capabilities, capsys):
    report = collect_doctor_report(CLIContext())
    render_doctor_report(CLIContext(), report)

    assert report["capabilities"] is None
    assert report["capabilities_error"] == "listing timed out"
    assert "Capabilities: UNAVAILABLE (listing timed out)" in capsys.readouterr().out


@patch("pyffmpegcore.cli.build_context", return_value=CLIContext())
@patch(
    "pyffmpegcore.cli.collect_doctor_report",
    return_value={"ffmpeg": {"available": True}, "ffprobe": {"available": True}, "capabilities_error": "timeout"},
)
def test_doctor_uses_environment_exit_code_when_capability_inspection_times_out(_mock_report, _mock_context, capsys):
    assert handle_doctor(argparse.Namespace(json=True)) == 3
    assert json.loads(capsys.readouterr().out)["capabilities_error"] == "timeout"


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
    assert payload["ffmpeg"]["configuration"] is not None
    assert payload["capabilities"]["encoder_count"] > 0
    assert payload["capabilities"]["filter_count"] > 0
    assert "libx264" in payload["capabilities"]["core_encoders"]
    assert "scale" in payload["capabilities"]["core_filters"]


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
    assert "--ffmpeg-path" in payload["ffmpeg"]["remedy"]
    assert "pyffmpegcore doctor" in payload["ffmpeg"]["remedy"]
    assert payload["capabilities"] is None


def test_doctor_human_report_includes_next_step_for_missing_ffprobe():
    result = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore", "doctor", "--ffprobe-path", "/definitely/missing/ffprobe"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 3
    assert "ffprobe: MISSING" in result.stdout
    assert "Remedy:" in result.stdout
    assert "--ffprobe-path" in result.stdout
