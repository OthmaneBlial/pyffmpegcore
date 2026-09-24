"""Public orchestration contracts shared by CLI, Python, and examples."""

from __future__ import annotations

import json
import sys

import pytest

from pyffmpegcore import (
    ConvertOptions,
    ExecutionPlan,
    FFprobeRunner,
    JobResult,
    JobStatus,
    MediaInfo,
    PreflightReport,
    PreparedWorkflow,
    StreamInfo,
    WorkflowEngine,
    WorkflowExecution,
)


def test_public_workflow_engine_preflights_before_mutation(tmp_path):
    engine = WorkflowEngine()
    output = tmp_path / "nested" / "output.mp4"
    plan = engine.planner.convert(
        str(tmp_path / "missing.webm"),
        str(output),
        ConvertOptions(video_codec="libx264", audio_codec="aac"),
    )

    prepared = engine.prepare(plan)
    batch = engine.run(prepared)
    payload = json.loads(json.dumps(batch.to_dict()))

    assert prepared.preflight.ok is False
    assert batch.succeeded is False
    assert batch.failed_count == 1
    assert payload["items"][0]["result"]["exit_category"] == "validation"
    assert not output.parent.exists()


def test_single_image_plan_is_typed_and_deterministic(tmp_path):
    engine = WorkflowEngine(ffmpeg_path="custom-ffmpeg", ffprobe_path="custom-ffprobe")

    first = engine.planner.image("source image.png", str(tmp_path / "output.webp"), quality=75, resize=(320, 180))
    second = engine.planner.image("source image.png", str(tmp_path / "output.webp"), quality=75, resize=(320, 180))

    assert first == second
    assert first.command[0] == "custom-ffmpeg"
    assert "scale=320:180" in first.command
    assert first.required_capabilities == ("filter:scale", "encoder:libwebp", "muxer:webp")


def test_workflow_execution_reports_before_after_target_proof(tmp_path):
    source = tmp_path / "source.bin"
    output = tmp_path / "output.bin"
    source.write_bytes(b"a" * 100)
    output.write_bytes(b"b" * 40)
    plan = ExecutionPlan(
        workflow="test/proof",
        command=("ffmpeg", "-version"),
        inputs=(str(source),),
        outputs=(str(output),),
        metadata={"target_size_bytes": 50},
    )
    prepared = PreparedWorkflow(plan, PreflightReport(plan.workflow, ()))
    result = JobResult(
        workflow=plan.workflow,
        command=plan.command,
        status=JobStatus.SUCCEEDED,
        exit_category="ok",
        returncode=0,
        elapsed_seconds=0.1,
    )
    execution = WorkflowExecution(
        str(source),
        str(output),
        prepared.preflight,
        result,
        plan.metadata,
    )

    assert execution.proof == {
        "input_size_bytes": 100,
        "output_size_bytes": 40,
        "size_change_bytes": -60,
        "reduction_percent": 60.0,
        "target_size_bytes": 50,
        "target_met": True,
    }
    assert execution.to_dict()["proof"] == execution.proof


def test_workflow_records_successful_output_probe(tmp_path, monkeypatch):
    output = tmp_path / "output.bin"
    code = f"from pathlib import Path; Path({str(output)!r}).write_bytes(b'media')"
    plan = ExecutionPlan(
        workflow="test/probed-output",
        command=(sys.executable, "-c", code),
        inputs=(),
        outputs=(str(output),),
    )
    media = MediaInfo(
        path=str(output),
        format_name="matroska",
        streams=(StreamInfo(index=0, codec_type="audio", codec_name="pcm_s16le"),),
    )
    monkeypatch.setattr(FFprobeRunner, "probe_media", lambda _runner, _path: media)
    prepared = PreparedWorkflow(plan, PreflightReport(plan.workflow, ()))

    result = WorkflowEngine(ffprobe_path="fake-ffprobe").run(prepared).items[0].result

    assert result.succeeded
    assert result.outputs[0]["verification"] == {
        "status": "probed",
        "format_name": "matroska",
        "duration": None,
        "size_bytes": None,
        "bit_rate": None,
        "streams": [
            {
                "index": 0,
                "type": "audio",
                "codec": "pcm_s16le",
                "width": None,
                "height": None,
                "pixel_format": None,
                "sample_rate": None,
                "channels": None,
                "language": None,
                "rotation": None,
            }
        ],
        "chapter_count": 0,
    }


def test_preserve_all_stream_contract_fails_when_output_layout_changes(tmp_path, monkeypatch):
    source = tmp_path / "source.mkv"
    source.touch()
    output = tmp_path / "output.mkv"
    code = f"from pathlib import Path; Path({str(output)!r}).write_bytes(b'media')"
    plan = ExecutionPlan(
        workflow="convert",
        command=(sys.executable, "-c", code),
        inputs=(str(source),),
        outputs=(str(output),),
        metadata={"stream_policy": "preserve-all"},
    )
    input_media = MediaInfo(
        path=str(source),
        streams=(
            StreamInfo(index=0, codec_type="video", codec_name="h264"),
            StreamInfo(index=1, codec_type="audio", codec_name="aac", language="eng"),
            StreamInfo(index=2, codec_type="subtitle", codec_name="subrip", language="fra"),
        ),
    )
    output_media = MediaInfo(
        path=str(output),
        streams=(
            StreamInfo(index=0, codec_type="video", codec_name="h264"),
            StreamInfo(index=1, codec_type="audio", codec_name="aac", language="eng"),
        ),
    )

    def probe_media(_runner, path):
        return input_media if path == str(source) else output_media

    monkeypatch.setattr(FFprobeRunner, "probe_media", probe_media)
    prepared = PreparedWorkflow(plan, PreflightReport(plan.workflow, ()))

    result = WorkflowEngine(ffprobe_path="fake-ffprobe").run(prepared).items[0].result

    assert result.status is JobStatus.FAILED
    assert result.exit_category == "validation"
    verification = result.outputs[0]["verification"]
    assert verification["stream_preservation"]["status"] == "failed"
    assert "subtitle/subrip/fra" in verification["reason"]


def test_preserve_all_remote_input_is_not_reprobed(tmp_path, monkeypatch):
    output = tmp_path / "remote-copy.mkv"
    code = f"from pathlib import Path; Path({str(output)!r}).write_bytes(b'media')"
    plan = ExecutionPlan(
        workflow="convert",
        command=(sys.executable, "-c", code),
        inputs=("https://example.invalid/media.mkv",),
        outputs=(str(output),),
        metadata={"stream_policy": "preserve-all"},
    )
    output_media = MediaInfo(
        path=str(output),
        streams=(StreamInfo(index=0, codec_type="video", codec_name="h264"),),
    )
    probed_paths = []

    def probe_media(_runner, path):
        probed_paths.append(path)
        return output_media

    monkeypatch.setattr(FFprobeRunner, "probe_media", probe_media)
    prepared = PreparedWorkflow(plan, PreflightReport(plan.workflow, ()))

    result = WorkflowEngine(ffprobe_path="fake-ffprobe").run(prepared).items[0].result

    assert result.succeeded
    assert probed_paths == [str(output)]
    assert result.outputs[0]["verification"]["stream_preservation"]["status"] == "unavailable"
    assert "all-stream preservation is unverified" in result.warnings[0]
    assert "example.invalid" not in " ".join(result.warnings)


@pytest.mark.parametrize(
    ("input_types", "output_types", "expected_status"),
    [
        (("video", "audio"), ("video",), JobStatus.FAILED),
        (("video",), ("video",), JobStatus.SUCCEEDED),
    ],
)
def test_convert_verifies_primary_streams_selected_from_local_input(
    tmp_path, monkeypatch, input_types, output_types, expected_status
):
    source = tmp_path / "source.mkv"
    source.touch()
    output = tmp_path / "output.mkv"
    code = f"from pathlib import Path; Path({str(output)!r}).write_bytes(b'media')"
    plan = ExecutionPlan(
        workflow="convert",
        command=(sys.executable, "-c", code),
        inputs=(str(source),),
        outputs=(str(output),),
        metadata={"stream_policy": "first-audio-video"},
    )
    input_media = MediaInfo(
        path=str(source),
        streams=tuple(StreamInfo(index=index, codec_type=kind) for index, kind in enumerate(input_types)),
    )
    output_media = MediaInfo(
        path=str(output),
        streams=tuple(StreamInfo(index=index, codec_type=kind) for index, kind in enumerate(output_types)),
    )
    monkeypatch.setattr(
        FFprobeRunner,
        "probe_media",
        lambda _runner, path: input_media if path == str(source) else output_media,
    )
    prepared = PreparedWorkflow(plan, PreflightReport(plan.workflow, ()))

    result = WorkflowEngine(ffprobe_path="fake-ffprobe").run(prepared).items[0].result

    verification = result.outputs[0]["verification"]["selected_streams"]
    assert result.status is expected_status
    assert verification["required_types"] == sorted(input_types)
    assert verification["output_types"] == sorted(output_types)
    assert verification["status"] == ("failed" if expected_status is JobStatus.FAILED else "verified")
    if expected_status is JobStatus.FAILED:
        assert (
            "expected output stream type 'audio' from input, found none" in result.outputs[0]["verification"]["reason"]
        )


def test_convert_does_not_probe_remote_input_for_selected_stream_verification(tmp_path, monkeypatch):
    output = tmp_path / "remote.mp4"
    code = f"from pathlib import Path; Path({str(output)!r}).write_bytes(b'media')"
    plan = ExecutionPlan(
        workflow="convert",
        command=(sys.executable, "-c", code),
        inputs=("https://user:secret@example.invalid/video.mp4",),
        outputs=(str(output),),
        metadata={"stream_policy": "first-audio-video"},
    )
    output_media = MediaInfo(
        path=str(output),
        streams=(StreamInfo(index=0, codec_type="video", codec_name="h264"),),
    )
    probed_paths = []

    def probe_media(_runner, path):
        probed_paths.append(path)
        return output_media

    monkeypatch.setattr(FFprobeRunner, "probe_media", probe_media)
    prepared = PreparedWorkflow(plan, PreflightReport(plan.workflow, ()))

    result = WorkflowEngine(ffprobe_path="fake-ffprobe").run(prepared).items[0].result

    assert result.succeeded
    assert probed_paths == [str(output)]
    assert result.outputs[0]["verification"]["selected_streams"] == {"status": "unavailable"}
    assert "selected-stream verification is unavailable" in result.warnings[0]
    assert "secret" not in " ".join(result.warnings)


def test_workflow_fails_when_ffprobe_rejects_output(tmp_path, monkeypatch):
    output = tmp_path / "invalid.bin"
    code = f"from pathlib import Path; Path({str(output)!r}).write_bytes(b'not media')"
    plan = ExecutionPlan(
        workflow="test/invalid-output",
        command=(sys.executable, "-c", code),
        inputs=(),
        outputs=(str(output),),
    )

    def reject_output(_runner, _path):
        raise RuntimeError("Invalid data found when processing input")

    monkeypatch.setattr(FFprobeRunner, "probe_media", reject_output)
    prepared = PreparedWorkflow(plan, PreflightReport(plan.workflow, ()))

    result = WorkflowEngine(ffprobe_path="fake-ffprobe").run(prepared).items[0].result

    assert result.status is JobStatus.FAILED
    assert result.exit_category == "validation"
    assert "Output verification failed" in result.stderr
    assert result.outputs[0]["verification"] == {
        "status": "failed",
        "reason": "Invalid data found when processing input",
    }


def test_workflow_fails_when_ffprobe_finds_no_streams(tmp_path, monkeypatch):
    output = tmp_path / "streamless.bin"
    code = f"from pathlib import Path; Path({str(output)!r}).write_bytes(b'media')"
    plan = ExecutionPlan(
        workflow="test/streamless-output",
        command=(sys.executable, "-c", code),
        inputs=(),
        outputs=(str(output),),
    )
    media = MediaInfo(path=str(output), format_name="matroska", streams=())
    monkeypatch.setattr(FFprobeRunner, "probe_media", lambda _runner, _path: media)
    prepared = PreparedWorkflow(plan, PreflightReport(plan.workflow, ()))

    result = WorkflowEngine(ffprobe_path="fake-ffprobe").run(prepared).items[0].result

    assert result.status is JobStatus.FAILED
    assert result.exit_category == "validation"
    assert result.outputs[0]["verification"] == {
        "status": "failed",
        "reason": "FFprobe found no media streams.",
    }


def test_workflow_fails_when_profile_output_codec_contract_is_broken(tmp_path, monkeypatch):
    output = tmp_path / "output.mp4"
    code = f"from pathlib import Path; Path({str(output)!r}).write_bytes(b'media')"
    plan = ExecutionPlan(
        workflow="profile/web/mp4-compatible",
        command=(sys.executable, "-c", code),
        inputs=(),
        outputs=(str(output),),
        metadata={"output_contract": {"codecs": {"video": "h264", "audio": "aac"}}},
    )
    media = MediaInfo(
        path=str(output),
        format_name="mp4",
        streams=(
            StreamInfo(index=0, codec_type="video", codec_name="hevc"),
            StreamInfo(index=1, codec_type="audio", codec_name="aac"),
        ),
    )
    monkeypatch.setattr(FFprobeRunner, "probe_media", lambda _runner, _path: media)
    prepared = PreparedWorkflow(plan, PreflightReport(plan.workflow, ()))

    result = WorkflowEngine(ffprobe_path="fake-ffprobe").run(prepared).items[0].result

    assert result.status is JobStatus.FAILED
    assert result.exit_category == "validation"
    assert result.outputs[0]["verification"]["status"] == "failed"
    assert result.outputs[0]["verification"]["reason"] == "expected h264 video, found hevc"
    assert "expected h264 video, found hevc" in result.stderr


def test_workflow_fails_when_profile_pixel_format_contract_is_broken(tmp_path, monkeypatch):
    output = tmp_path / "output.mp4"
    code = f"from pathlib import Path; Path({str(output)!r}).write_bytes(b'media')"
    plan = ExecutionPlan(
        workflow="profile/web/mp4-compatible",
        command=(sys.executable, "-c", code),
        inputs=(),
        outputs=(str(output),),
        metadata={"output_contract": {"pixel_formats": {"video": "yuv420p"}}},
    )
    media = MediaInfo(
        path=str(output),
        format_name="mp4",
        streams=(StreamInfo(index=0, codec_type="video", codec_name="h264", details={"pix_fmt": "yuv422p"}),),
    )
    monkeypatch.setattr(FFprobeRunner, "probe_media", lambda _runner, _path: media)
    prepared = PreparedWorkflow(plan, PreflightReport(plan.workflow, ()))

    result = WorkflowEngine(ffprobe_path="fake-ffprobe").run(prepared).items[0].result

    assert result.status is JobStatus.FAILED
    assert result.exit_category == "validation"
    assert result.outputs[0]["verification"]["streams"][0]["pixel_format"] == "yuv422p"
    assert result.outputs[0]["verification"]["reason"] == ("expected yuv420p pixel format for video, found yuv422p")


@pytest.mark.parametrize(("language", "actual"), [("eng", "eng"), (None, "unknown")])
def test_workflow_fails_when_profile_subtitle_language_contract_is_broken(tmp_path, monkeypatch, language, actual):
    output = tmp_path / "output.mp4"
    code = f"from pathlib import Path; Path({str(output)!r}).write_bytes(b'media')"
    plan = ExecutionPlan(
        workflow="profile/subtitles/accessibility",
        command=(sys.executable, "-c", code),
        inputs=(),
        outputs=(str(output),),
        metadata={"output_contract": {"stream_languages": {"subtitle": "fra"}}},
    )
    media = MediaInfo(
        path=str(output),
        format_name="mp4",
        streams=(StreamInfo(index=0, codec_type="subtitle", codec_name="mov_text", language=language),),
    )
    monkeypatch.setattr(FFprobeRunner, "probe_media", lambda _runner, _path: media)
    prepared = PreparedWorkflow(plan, PreflightReport(plan.workflow, ()))

    result = WorkflowEngine(ffprobe_path="fake-ffprobe").run(prepared).items[0].result

    assert result.status is JobStatus.FAILED
    assert result.exit_category == "validation"
    assert result.outputs[0]["verification"]["reason"] == f"expected fra subtitle language, found {actual}"


def test_workflow_fails_when_profile_requires_a_missing_output_stream(tmp_path, monkeypatch):
    output = tmp_path / "output.m4a"
    code = f"from pathlib import Path; Path({str(output)!r}).write_bytes(b'media')"
    plan = ExecutionPlan(
        workflow="profile/audio/podcast-speech",
        command=(sys.executable, "-c", code),
        inputs=(),
        outputs=(str(output),),
        metadata={
            "output_contract": {
                "codecs": {"audio": "aac"},
                "required_stream_types": ["audio"],
            }
        },
    )
    media = MediaInfo(
        path=str(output),
        format_name="mp4",
        streams=(StreamInfo(index=0, codec_type="video", codec_name="h264"),),
    )
    monkeypatch.setattr(FFprobeRunner, "probe_media", lambda _runner, _path: media)
    prepared = PreparedWorkflow(plan, PreflightReport(plan.workflow, ()))

    result = WorkflowEngine(ffprobe_path="fake-ffprobe").run(prepared).items[0].result

    assert result.status is JobStatus.FAILED
    assert result.exit_category == "validation"
    assert result.outputs[0]["verification"]["reason"] == "expected output stream type 'audio', found none"


def test_workflow_fails_when_concat_output_loses_required_audio(tmp_path, monkeypatch):
    output = tmp_path / "joined.mp4"
    code = f"from pathlib import Path; Path({str(output)!r}).write_bytes(b'media')"
    plan = ExecutionPlan(
        workflow="concat/reencode",
        command=(sys.executable, "-c", code),
        inputs=(),
        outputs=(str(output),),
        metadata={"output_contract": {"required_stream_types": ["video", "audio"]}},
    )
    media = MediaInfo(
        path=str(output),
        format_name="mp4",
        streams=(StreamInfo(index=0, codec_type="video", codec_name="h264"),),
    )
    monkeypatch.setattr(FFprobeRunner, "probe_media", lambda _runner, _path: media)
    prepared = PreparedWorkflow(plan, PreflightReport(plan.workflow, ()))

    result = WorkflowEngine(ffprobe_path="fake-ffprobe").run(prepared).items[0].result

    assert result.status is JobStatus.FAILED
    assert result.exit_category == "validation"
    assert result.outputs[0]["verification"]["reason"] == "expected output stream type 'audio', found none"


def test_workflow_fails_when_audio_only_conversion_loses_audio(tmp_path, monkeypatch):
    output = tmp_path / "audio.m4a"
    code = f"from pathlib import Path; Path({str(output)!r}).write_bytes(b'media')"
    plan = ExecutionPlan(
        workflow="convert",
        command=(sys.executable, "-c", code),
        inputs=("source.mkv",),
        outputs=(str(output),),
        metadata={"stream_policy": "audio-only", "required_stream_types": ["audio"]},
    )
    media = MediaInfo(
        path=str(output),
        format_name="mp4",
        streams=(StreamInfo(index=0, codec_type="video", codec_name="h264"),),
    )
    monkeypatch.setattr(FFprobeRunner, "probe_media", lambda _runner, _path: media)
    prepared = PreparedWorkflow(plan, PreflightReport(plan.workflow, ()))

    result = WorkflowEngine(ffprobe_path="fake-ffprobe").run(prepared).items[0].result

    assert result.status is JobStatus.FAILED
    assert result.exit_category == "validation"
    assert result.outputs[0]["verification"]["reason"] == "expected output stream type 'audio', found none"


def test_workflow_marks_output_unverified_when_ffprobe_is_unavailable(tmp_path, monkeypatch):
    output = tmp_path / "output.bin"
    code = f"from pathlib import Path; Path({str(output)!r}).write_bytes(b'media')"
    plan = ExecutionPlan(
        workflow="test/no-ffprobe",
        command=(sys.executable, "-c", code),
        inputs=(),
        outputs=(str(output),),
    )

    def unavailable(_runner, _path):
        raise RuntimeError("FFprobe executable 'missing-ffprobe' was not found.")

    monkeypatch.setattr(FFprobeRunner, "probe_media", unavailable)
    prepared = PreparedWorkflow(plan, PreflightReport(plan.workflow, ()))

    result = WorkflowEngine(ffprobe_path="missing-ffprobe").run(prepared).items[0].result

    assert result.succeeded
    assert result.outputs[0]["verification"] == {
        "status": "unavailable",
        "reason": "FFprobe executable 'missing-ffprobe' was not found.",
    }
    assert any("Output media could not be probed" in warning for warning in result.warnings)
