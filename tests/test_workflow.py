"""Public orchestration contracts shared by CLI, Python, and examples."""

from __future__ import annotations

import json

from pyffmpegcore import (
    ConvertOptions,
    ExecutionPlan,
    JobResult,
    JobStatus,
    PreflightReport,
    PreparedWorkflow,
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
