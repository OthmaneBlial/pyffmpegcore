"""Deterministic shared workflow planning contracts."""

from __future__ import annotations

import json

import pytest

from pyffmpegcore import (
    CompressOptions,
    ConvertOptions,
    ExecutionPlan,
    ResizeOptions,
    ValidationError,
    WorkflowPlanner,
    parse_size,
)
from pyffmpegcore.domain import MediaInfo, StreamInfo
from pyffmpegcore.planning import parse_bitrate
from pyffmpegcore.preflight import PreflightReport
from pyffmpegcore.presentation import render_plan_text


def test_execution_plan_metadata_is_deeply_immutable_and_serializes_to_plain_values():
    metadata = {"contract": {"required_stream_types": ["video"]}}
    plan = ExecutionPlan(
        workflow="test",
        command=("ffmpeg",),
        inputs=(),
        outputs=(),
        metadata=metadata,
    )

    metadata["contract"]["required_stream_types"].append("audio")
    assert plan.metadata["contract"]["required_stream_types"] == ["video"]
    with pytest.raises(TypeError, match="metadata is immutable"):
        plan.metadata["contract"]["required_stream_types"].append("audio")
    with pytest.raises(TypeError, match="metadata is immutable"):
        plan.metadata["contract"]["required_stream_types"][0] = "audio"
    with pytest.raises(TypeError, match="metadata is immutable"):
        plan.metadata["contract"]["optional"] = True

    payload = plan.to_dict()
    assert type(payload["metadata"]) is dict
    assert type(payload["metadata"]["contract"]) is dict
    assert type(payload["metadata"]["contract"]["required_stream_types"]) is list
    payload["metadata"]["contract"]["required_stream_types"].append("audio")
    assert plan.metadata["contract"]["required_stream_types"] == ["video"]


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


def test_convert_plan_can_preserve_every_stream_without_reencoding(tmp_path):
    source = tmp_path / "input rich.mkv"
    output = tmp_path / "output rich.mkv"

    plan = WorkflowPlanner().convert(
        str(source),
        str(output),
        ConvertOptions(preserve_all_streams=True),
    )

    assert plan.command[plan.command.index("-map") + 1] == "0"
    assert plan.command[plan.command.index("-c") + 1] == "copy"
    assert "-c:v" not in plan.command
    assert "-c:a" not in plan.command
    assert plan.selected_streams == ("all input streams",)
    assert plan.metadata["stream_policy"] == "preserve-all"
    assert "output container" in plan.warnings[0]


def test_concat_reencode_plan_selects_first_tracks_and_resets_timestamps(tmp_path):
    plan = WorkflowPlanner().concat(
        [str(tmp_path / "one.mp4"), str(tmp_path / "two.webm")],
        str(tmp_path / "joined.mp4"),
        mode="reencode",
    )
    graph = plan.command[plan.command.index("-filter_complex") + 1]

    assert plan.selected_streams == ("video:0", "audio:0")
    assert "[0:v:0]setpts=PTS-STARTPTS[v0]" in graph
    assert "[0:a:0]asetpts=PTS-STARTPTS[a0]" in graph
    assert "[v0][a0][v1][a1]concat=n=2:v=1:a=1[vout][aout]" in graph
    assert plan.metadata["required_stream_types"] == ["video", "audio"]
    assert plan.metadata["output_contract"] == {"required_stream_types": ["video", "audio"]}
    assert "omit all other streams" in plan.operations[1]
    preview = render_plan_text(plan, PreflightReport(workflow=plan.workflow, checks=()), explain=True)
    assert "select the first video and audio stream" in preview
    assert "omit all other streams" in preview


def test_concat_copy_plan_maps_every_input_stream(tmp_path):
    plan = WorkflowPlanner().concat(
        [str(tmp_path / "one.mkv"), str(tmp_path / "two.mkv")],
        str(tmp_path / "joined.mkv"),
        mode="copy",
    )

    assert plan.command[plan.command.index("-map") + 1] == "0"
    assert plan.selected_streams == ("all input streams",)
    assert "all matching input streams" in plan.operations[0]
    assert plan.metadata["stream_policy"] == "preserve-all"


def test_core_media_plans_declare_primary_output_streams(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "pyffmpegcore.planning.FFprobeRunner.probe",
        lambda _runner, _path: {"audio": {"sample_rate": 48_000}, "video": {"duration": 1}},
    )
    planner = WorkflowPlanner()
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "still.png").write_bytes(b"image")
    video = str(tmp_path / "video.mp4")
    audio = str(tmp_path / "audio.wav")
    subtitle = str(tmp_path / "captions.srt")

    plans = (
        (planner.resize(video, str(tmp_path / "resized.mp4"), ResizeOptions(320, 180)), ["video"]),
        (planner.compress(video, str(tmp_path / "compressed.mp4")), ["video"]),
        (planner.extract_audio(video, str(tmp_path / "audio.m4a")), ["audio"]),
        (planner.thumbnail(video, str(tmp_path / "thumb.png")), ["video"]),
        (planner.waveform(audio, str(tmp_path / "wave.png")), ["video"]),
        (planner.speed("video", video, str(tmp_path / "fast.mp4"), factor=2), ["video", "audio"]),
        (planner.speed("audio", audio, str(tmp_path / "fast.m4a"), factor=2), ["audio"]),
        (
            planner.subtitles("add", video, str(tmp_path / "subtitled.mp4"), subtitle_file=subtitle),
            ["video", "subtitle"],
        ),
        (planner.subtitles("extract", video, str(tmp_path / "captions.srt")), ["subtitle"]),
        (
            planner.subtitles("burn", video, str(tmp_path / "burned.mp4"), subtitle_file=subtitle),
            ["video"],
        ),
        (planner.mix_audio("mix", [audio, audio], str(tmp_path / "mix.m4a")), ["audio"]),
        (planner.normalize_audio(audio, str(tmp_path / "normalized.m4a")), ["audio"]),
        (planner.images("convert", str(image_dir), str(tmp_path / "converted")), ["video"]),
        (planner.image(str(image_dir / "still.png"), str(tmp_path / "copy.png")), ["video"]),
    )

    for plan, expected in plans:
        assert plan.metadata["output_contract"]["required_stream_types"] == expected, plan.workflow

    copy_plan = planner.concat([video, video], str(tmp_path / "joined.mp4"), mode="copy")
    assert copy_plan.metadata["stream_policy"] == "preserve-all"


@pytest.mark.parametrize("factor", [float("nan"), float("inf"), float("-inf")])
def test_speed_rejects_nonfinite_factors_before_probing(tmp_path, monkeypatch, factor):
    monkeypatch.setattr(
        "pyffmpegcore.planning.FFprobeRunner.probe",
        lambda *_args: pytest.fail("non-finite speed factor reached FFprobe"),
    )

    with pytest.raises(ValidationError, match="speed factor must be positive and finite"):
        WorkflowPlanner().speed("audio", str(tmp_path / "input.wav"), str(tmp_path / "output.wav"), factor=factor)


@pytest.mark.parametrize(
    ("options", "expected_warning"),
    [
        (
            ConvertOptions(),
            "Other video or audio streams, subtitles, data streams, and attachments are omitted",
        ),
        (
            ConvertOptions(audio_only=True),
            "Only the first audio stream is selected; video, other audio streams, subtitles, data streams,",
        ),
    ],
)
def test_convert_plan_warns_about_omitted_streams(tmp_path, options, expected_warning):
    plan = WorkflowPlanner().convert(str(tmp_path / "input.mkv"), str(tmp_path / "output.mp4"), options)

    assert expected_warning in plan.warnings[0]
    preview = render_plan_text(plan, PreflightReport(workflow="convert", checks=()), explain=True)
    assert "Warnings:" in preview
    assert expected_warning in preview


@pytest.mark.parametrize(
    "options",
    [
        ConvertOptions(video_codec="copy"),
        ConvertOptions(audio_codec="copy"),
        ConvertOptions(audio_only=True),
        ConvertOptions(threads=1),
        ConvertOptions(hardware_acceleration="auto"),
    ],
)
def test_preserve_all_streams_rejects_conflicting_conversion_options(options):
    values = {
        field: getattr(options, field)
        for field in ConvertOptions.__dataclass_fields__
        if field != "preserve_all_streams"
    }
    with pytest.raises(ValidationError, match="preserve_all_streams cannot be combined"):
        ConvertOptions(**values, preserve_all_streams=True)


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
    media = MediaInfo(
        path=str(source),
        duration=10.0,
        streams=(StreamInfo(index=0, codec_type="video"), StreamInfo(index=1, codec_type="audio")),
    )
    monkeypatch.setattr("pyffmpegcore.planning.FFprobeRunner.probe_media", lambda _self, _path: media)
    planner = WorkflowPlanner()
    options = CompressOptions(target_size_bytes=parse_size("5MB"), minimum_video_bitrate=100_000)

    plan = planner.compress(str(source), str(output), options)

    assert [step.name for step in plan.steps] == ["analysis-pass", "encode-pass"]
    assert all("<pyffmpegcore-passlog>" in step.command for step in plan.steps)
    assert plan.selected_streams == ("video", "audio")
    assert "encoder:aac" in plan.required_capabilities
    assert "-c:a" in plan.steps[1].command
    assert any("reserve 128k audio" in operation for operation in plan.operations)
    assert plan.metadata["target_size_bytes"] == 5_000_000
    assert plan.metadata["minimum_feasible_bytes"] > 0
    assert any("quality floor" in operation for operation in plan.operations)


def test_target_size_video_only_plan_uses_full_budget_for_video(tmp_path, monkeypatch):
    source = tmp_path / "silent.webm"
    media = MediaInfo(path=str(source), duration=10.0, streams=(StreamInfo(index=0, codec_type="video"),))
    monkeypatch.setattr("pyffmpegcore.planning.FFprobeRunner.probe_media", lambda _self, _path: media)
    options = CompressOptions(target_size_bytes=parse_size("1MiB"))

    plan = WorkflowPlanner().compress(str(source), str(tmp_path / "output.mp4"), options)
    encode_step = plan.steps[1].command

    assert plan.selected_streams == ("video",)
    assert "encoder:libx264" in plan.required_capabilities
    assert "encoder:aac" not in plan.required_capabilities
    assert "-c:a" not in encode_step
    assert "-b:a" not in encode_step
    expected_bitrate = int(
        options.target_size_bytes * (1 - options.container_overhead_percent / 100) * 8 / media.duration
    )
    assert encode_step[encode_step.index("-b:v") + 1] == str(expected_bitrate)
    assert any("input has no audio stream" in operation for operation in plan.operations)
    assert not any("reserve 128k audio" in operation for operation in plan.operations)
    with pytest.raises(ValidationError, match="bitrate must be"):
        WorkflowPlanner().compress(
            str(source),
            str(tmp_path / "invalid-bitrate.mp4"),
            CompressOptions(target_size_bytes=parse_size("1MiB"), audio_bitrate="invalid"),
        )


def test_target_size_plan_rejects_an_impossible_request(tmp_path, monkeypatch):
    media = MediaInfo(
        path=str(tmp_path / "input.mp4"),
        duration=60.0,
        streams=(StreamInfo(index=0, codec_type="video"), StreamInfo(index=1, codec_type="audio")),
    )
    monkeypatch.setattr("pyffmpegcore.planning.FFprobeRunner.probe_media", lambda _self, _path: media)
    planner = WorkflowPlanner()
    options = CompressOptions(target_size_bytes=1024, minimum_video_bitrate=100_000)

    with pytest.raises(ValidationError, match="target is not feasible"):
        planner.compress(str(tmp_path / "input.mp4"), str(tmp_path / "output.mp4"), options)


def test_image_plan_rejects_an_empty_directory(tmp_path):
    with pytest.raises(ValidationError, match="no supported images"):
        WorkflowPlanner().images("convert", str(tmp_path), str(tmp_path / "output"))


def test_image_plan_rejects_symlinked_output_that_escapes_output_directory(tmp_path):
    source_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    source_dir.mkdir()
    output_dir.mkdir()
    (source_dir / "sample.png").write_bytes(b"placeholder")
    destination = output_dir / "sample.jpg"
    outside_target = tmp_path / "outside.jpg"
    try:
        destination.symlink_to(outside_target)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(ValidationError, match="refusing symlinked image output"):
        WorkflowPlanner().images("convert", str(source_dir), str(output_dir))

    assert destination.is_symlink()
    assert not outside_target.exists()
