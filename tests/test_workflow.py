"""Public orchestration contracts shared by CLI, Python, and examples."""

from __future__ import annotations

import json

from pyffmpegcore import ConvertOptions, WorkflowEngine


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
