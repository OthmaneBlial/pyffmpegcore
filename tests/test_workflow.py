"""Public orchestration contracts shared by CLI, Python, and examples."""

from __future__ import annotations

import json
import sys

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
                "sample_rate": None,
                "channels": None,
                "language": None,
                "rotation": None,
            }
        ],
        "chapter_count": 0,
    }


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
