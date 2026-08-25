"""Contracts for the typed runner facade and guarded low-level escape hatch."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from pyffmpegcore import JobResult, JobStatus, OverwritePolicy, ProgressEvent, ValidationError
from pyffmpegcore.runner import FFmpegRunner


def _result() -> JobResult:
    return JobResult(
        workflow="test",
        command=("ffmpeg",),
        status=JobStatus.SUCCEEDED,
        exit_category="ok",
        returncode=0,
        elapsed_seconds=0.1,
    )


def test_init_and_planner_propagate_custom_paths():
    runner = FFmpegRunner("/custom/ffmpeg", "/custom/ffprobe")

    assert runner.ffmpeg_path == "/custom/ffmpeg"
    assert runner.ffprobe_path == "/custom/ffprobe"
    assert runner.planner.ffmpeg_path == "/custom/ffmpeg"
    assert runner.planner.ffprobe_path == "/custom/ffprobe"


@patch("subprocess.run")
def test_low_level_run_injects_safe_overwrite_refusal(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(["ffmpeg"], 0, "output", "")

    result = FFmpegRunner().run(["-version"])

    assert result.returncode == 0
    assert mock_run.call_args.args[0] == ["ffmpeg", "-n", "-version"]
    assert mock_run.call_args.kwargs == {"capture_output": True, "text": True}


@patch("subprocess.run")
def test_low_level_run_respects_visible_overwrite_flag(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(["ffmpeg"], 0, "", "")

    FFmpegRunner().run(["-y", "-i", "input.mp4", "output.mp4"], overwrite=OverwritePolicy.REPLACE)

    assert mock_run.call_args.args[0].count("-y") == 1
    assert "-n" not in mock_run.call_args.args[0]


@patch("subprocess.run")
def test_low_level_run_annotates_failures(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(["ffmpeg"], 1, "", "boom")

    result = FFmpegRunner().run(["-version"])

    assert "FFmpeg command failed with exit code 1." in result.stderr
    assert "Command: ffmpeg -n -version" in result.stderr
    assert "boom" in result.stderr


@patch("subprocess.run", side_effect=FileNotFoundError("missing"))
def test_low_level_run_reports_missing_binary(_mock_run):
    with pytest.raises(RuntimeError, match="FFmpeg executable '/missing/ffmpeg' was not found"):
        FFmpegRunner("/missing/ffmpeg").run(["-version"])


@patch("pyffmpegcore.runner.FFmpegRunner._run_workflow")
def test_convert_compiles_typed_options(run_workflow):
    run_workflow.return_value = _result()
    runner = FFmpegRunner()

    result = runner.convert(
        "input.mp4",
        "output.mp4",
        video_codec="libx264",
        audio_codec="aac",
        threads=4,
    )
    plan = run_workflow.call_args.args[0]

    assert result.succeeded
    assert ("-c:v", "libx264") == (
        plan.command[plan.command.index("-c:v")],
        plan.command[plan.command.index("-c:v") + 1],
    )
    assert "4" in plan.command


def test_resize_rejects_non_positive_dimensions():
    with pytest.raises(ValidationError, match="width and height must be positive"):
        FFmpegRunner().resize("input.mp4", "output.mp4", 0, 480)


@patch("pyffmpegcore.runner.FFmpegRunner._run_workflow")
def test_compress_compiles_typed_single_pass_options(run_workflow):
    run_workflow.return_value = _result()

    FFmpegRunner().compress("input.mp4", "output.mp4", crf=28, two_pass=False, video_bitrate="1000k")
    plan = run_workflow.call_args.args[0]

    assert "1000k" in plan.command
    assert "-crf" not in plan.command


def test_compress_rejects_invalid_target_size():
    with pytest.raises(ValueError, match="target_size_kb must be a positive integer"):
        FFmpegRunner().compress("input.mp4", "output.mp4", target_size_kb=0)


@patch("pyffmpegcore.planning.FFprobeRunner.get_duration", return_value=60.0)
def test_compress_rejects_target_below_quality_floor(_duration):
    with pytest.raises(ValidationError, match="not feasible.*quality floor.*use at least"):
        FFmpegRunner().compress(
            "input.mp4",
            "output.mp4",
            target_size_kb=100,
            minimum_video_bitrate=100_000,
        )


@patch("pyffmpegcore.runner.FFmpegRunner._run_workflow")
def test_extract_audio_uses_extension_codec_and_forwards_progress(run_workflow):
    run_workflow.return_value = _result()
    callback = MagicMock()

    FFmpegRunner().extract_audio("input.mp4", "output.mp3", progress_callback=callback)
    plan = run_workflow.call_args.args[0]

    assert "libmp3lame" in plan.command
    assert run_workflow.call_args.kwargs["progress_callback"] is callback


@patch("subprocess.run")
def test_get_version(mock_run):
    mock_run.return_value = MagicMock(stdout="ffmpeg version 9.0\n")

    assert FFmpegRunner().get_version() == "ffmpeg version 9.0"


def test_progress_event_is_the_typed_callback_contract():
    event = ProgressEvent(status="running", frame=12, time_seconds=0.5, speed=2.0)

    assert event.to_dict()["frame"] == 12
