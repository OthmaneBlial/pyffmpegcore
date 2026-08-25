"""Deterministic shared workflow planning contracts."""

from __future__ import annotations

import json

import pytest

from pyffmpegcore import CompressOptions, ConvertOptions, ValidationError, WorkflowPlanner, parse_size
from pyffmpegcore.planning import parse_bitrate


def test_convert_plan_is_deterministic_and_uses_an_argument_vector(tmp_path):
    source = tmp_path / "input clip.mp4"
    output = tmp_path / "output clip.mp4"
    options = ConvertOptions(video_codec="libx264", audio_codec="aac")
    planner = WorkflowPlanner(ffmpeg_path="/tools/ffmpeg", ffprobe_path="/tools/ffprobe")

    first = planner.convert(str(source), str(output), options)
    second = planner.convert(str(source), str(output), options)

    assert first == second
    assert first.command[0] == "/tools/ffmpeg"
    assert first.command[1] == "-n"
    assert first.command[2] == "-nostdin"
    assert "-y" not in first.command
    assert first.outputs == (str(output.resolve()),)
    payload = json.loads(json.dumps(first.to_dict()))
    assert isinstance(payload["command"], list)
    assert payload["operations"][2] == "video codec: libx264"
    assert first.command[first.command.index("-map") + 1] == "0:v:0?"
    assert first.command.count("-map") == 2
    assert "-map_metadata" in first.command
    assert "-map_chapters" in first.command


@pytest.mark.parametrize(
    ("value", "expected"),
    [("25MB", 25_000_000), ("25MiB", 25 * 1024 * 1024), ("1.5GB", 1_500_000_000), ("42", 42)],
)
def test_parse_size_uses_explicit_decimal_and_binary_units(value, expected):
    assert parse_size(value) == expected


@pytest.mark.parametrize(("value", "expected"), [("100k", 100_000), ("1.5M", 1_500_000), ("2g", 2_000_000_000)])
def test_parse_bitrate_accepts_documented_suffixes(value, expected):
    assert parse_bitrate(value) == expected


def test_parse_bitrate_rejects_invalid_values():
    with pytest.raises(ValidationError, match="bitrate must be"):
        parse_bitrate("fast")


def test_target_size_plan_has_two_exact_steps_and_an_honest_floor(tmp_path, monkeypatch):
    source = tmp_path / "input.mp4"
    output = tmp_path / "output.mp4"
    monkeypatch.setattr("pyffmpegcore.planning.FFprobeRunner.get_duration", lambda _self, _path: 10.0)
    planner = WorkflowPlanner()
    options = CompressOptions(target_size_bytes=parse_size("5MB"), minimum_video_bitrate=100_000)

    plan = planner.compress(str(source), str(output), options)

    assert [step.name for step in plan.steps] == ["analysis-pass", "encode-pass"]
    assert all("<pyffmpegcore-passlog>" in step.command for step in plan.steps)
    assert plan.metadata["target_size_bytes"] == 5_000_000
    assert plan.metadata["minimum_feasible_bytes"] > 0
    assert any("quality floor" in operation for operation in plan.operations)


def test_target_size_plan_rejects_an_impossible_request(tmp_path, monkeypatch):
    monkeypatch.setattr("pyffmpegcore.planning.FFprobeRunner.get_duration", lambda _self, _path: 60.0)
    planner = WorkflowPlanner()
    options = CompressOptions(target_size_bytes=1024, minimum_video_bitrate=100_000)

    with pytest.raises(ValidationError, match="target is not feasible"):
        planner.compress(str(tmp_path / "input.mp4"), str(tmp_path / "output.mp4"), options)


def test_image_plan_rejects_an_empty_directory(tmp_path):
    with pytest.raises(ValidationError, match="no supported images"):
        WorkflowPlanner().images("convert", str(tmp_path), str(tmp_path / "output"))
