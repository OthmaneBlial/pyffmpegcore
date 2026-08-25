"""Contract tests for plan -> preflight -> run -> machine result CLI flow."""

from __future__ import annotations

import json

import pytest

from pyffmpegcore.cli import main
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_result_json_executes_the_same_exact_plan(tmp_path, capsys):
    """The command shown in a plan must be the command used by the executor."""
    video = ensure_downloaded_media()["video_mp4_h264_1080p"]
    output = tmp_path / "thumb.jpg"

    returncode = main(
        [
            "thumbnail",
            "--input",
            str(video),
            "--output",
            str(output),
            "--result-json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert returncode == 0, captured.err
    assert captured.err == ""
    assert payload["schema_version"] == "1.0"
    assert payload["preflight"]["ok"] is True
    assert payload["plan"]["command"] == payload["items"][0]["result"]["command"]
    assert payload["items"][0]["result"]["status"] == "succeeded"
    assert payload["summary"] == {"total": 1, "succeeded": 1, "failed": 0}
    assert output.is_file()


def test_result_json_reports_preflight_failure_without_mutation(tmp_path, capsys):
    """Automation receives parseable failure facts and no partial output tree."""
    missing = tmp_path / "missing.mp4"
    output = tmp_path / "nested" / "output.mp4"

    returncode = main(
        [
            "convert",
            "--input",
            str(missing),
            "--output",
            str(output),
            "--result-json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert returncode == 4
    assert captured.err == ""
    assert payload["preflight"]["ok"] is False
    assert payload["items"][0]["result"]["exit_category"] == "validation"
    assert not output.parent.exists()


def test_result_json_rejects_preview_combination(capsys):
    """Machine plan and machine result modes remain unambiguous contracts."""
    returncode = main(["doctor", "--result-json", "--dry-run"])
    captured = capsys.readouterr()

    assert returncode == 2
    assert "cannot be combined" in captured.err
    assert captured.out == ""


def test_target_size_missing_input_is_a_validation_error(tmp_path, capsys):
    """Probe-dependent planning failures should retain the validation category."""
    missing = tmp_path / "missing.mp4"
    returncode = main(
        [
            "compress",
            "--input",
            str(missing),
            "--output",
            str(tmp_path / "output.mp4"),
            "--target-size",
            "2MB",
        ]
    )
    captured = capsys.readouterr()

    assert returncode == 4
    assert "input cannot be inspected" in captured.err


def test_result_json_missing_ffmpeg_is_an_environment_error(tmp_path, capsys):
    """A missing execution engine remains the stable environment category."""
    source = tmp_path / "input.mp4"
    source.write_bytes(b"placeholder")

    returncode = main(
        [
            "convert",
            "--input",
            str(source),
            "--output",
            str(tmp_path / "output.mp4"),
            "--ffmpeg-path",
            str(tmp_path / "missing-ffmpeg"),
            "--result-json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert returncode == 3
    assert captured.err == ""
    assert payload["items"][0]["result"]["exit_category"] == "environment"
