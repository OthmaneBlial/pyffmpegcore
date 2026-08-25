"""Strict schema, DAG, secret, preflight, and migration pipeline contracts."""

from __future__ import annotations

import json
import threading

import pytest

from pyffmpegcore import (
    PipelineCompiler,
    PipelineRunner,
    PipelineSpec,
    ValidationError,
    migrate_pipeline_document,
)


def _document(source: str) -> dict:
    return {
        "schema_version": "1.0",
        "name": "web_publish",
        "description": "Publish a web video and a proof thumbnail.",
        "variables": {"SOURCE": source, "OUTPUT_DIR": "build"},
        "cache": {"enabled": True, "directory": ".cache", "content_aware": True},
        "steps": [
            {
                "id": "thumbnail",
                "workflow": "thumbnail",
                "input": "${steps.web.output}",
                "output": "${OUTPUT_DIR}/poster.jpg",
                "options": {"timestamp": "00:00:00.100", "width": 320},
            },
            {
                "id": "web",
                "profile": "web/mp4-compatible",
                "input": "${SOURCE}",
                "output": "${OUTPUT_DIR}/publish.mp4",
            },
        ],
    }


def test_pipeline_compiles_topologically_and_renders_three_graph_formats(tmp_path):
    source = tmp_path / "source ü.mkv"
    source.write_bytes(b"media")
    pipeline = PipelineCompiler().compile(PipelineSpec.from_dict(_document(str(source)), base_dir=tmp_path))

    assert [step.id for step in pipeline.steps] == ["web", "thumbnail"]
    assert pipeline.steps[1].needs == ("web",)
    assert pipeline.steps[1].plan.inputs == pipeline.steps[0].plan.outputs
    assert pipeline.steps[0].plan.command[0] == "ffmpeg"
    assert "shell" not in json.dumps(pipeline.to_dict()).casefold()
    assert "web <- <source>" in pipeline.graph("text")
    assert "web --> thumbnail" in pipeline.graph("mermaid")
    assert '"web" -> "thumbnail"' in pipeline.graph("dot")


def test_pipeline_rejects_raw_commands_cycles_collisions_and_unknown_options(tmp_path):
    document = _document("source.mkv")
    document["steps"][0]["command"] = "ffmpeg -i input output"
    with pytest.raises(ValidationError, match="unknown pipeline step fields"):
        PipelineSpec.from_dict(document, base_dir=tmp_path)

    cycle = _document("source.mkv")
    cycle["steps"][1]["input"] = "${steps.thumbnail.output}"
    with pytest.raises(ValidationError, match="cycle"):
        PipelineCompiler().compile(PipelineSpec.from_dict(cycle, base_dir=tmp_path))

    collision = _document("source.mkv")
    collision["steps"][0]["output"] = "${OUTPUT_DIR}/publish.mp4"
    with pytest.raises(ValidationError, match="output collision"):
        PipelineCompiler().compile(PipelineSpec.from_dict(collision, base_dir=tmp_path))

    options = _document("source.mkv")
    options["steps"][0]["options"]["arbitrary_filter"] = "unsafe"
    with pytest.raises(ValidationError, match="unknown thumbnail options"):
        PipelineCompiler().compile(PipelineSpec.from_dict(options, base_dir=tmp_path))


def test_pipeline_secret_values_live_outside_the_file_and_are_masked(tmp_path):
    document = {
        "schema_version": "1.0",
        "name": "remote_source",
        "secret_variables": ["SOURCE_URL"],
        "steps": [
            {
                "id": "web",
                "profile": "web/mp4-compatible",
                "input": "${SOURCE_URL}",
                "output": "publish.mp4",
            }
        ],
    }
    spec = PipelineSpec.from_dict(document, base_dir=tmp_path)
    with pytest.raises(ValidationError, match="missing secret"):
        PipelineCompiler().compile(spec)

    secret = "https://user:very-private-token@example.invalid/video.mp4?token=very-private-token"
    pipeline = PipelineCompiler().compile(spec, variables={"SOURCE_URL": secret})
    rendered = json.dumps(pipeline.to_dict())
    assert "very-private-token" not in rendered
    assert "<redacted>" in rendered

    inline = dict(document)
    inline["variables"] = {"SOURCE_URL": secret}
    with pytest.raises(ValidationError, match="must not have values"):
        PipelineSpec.from_dict(inline, base_dir=tmp_path)


def test_pipeline_schema_migration_is_explicit_and_canonical(tmp_path):
    source = _document("source.mkv")
    migrated = migrate_pipeline_document(source)
    assert migrated["schema_version"] == "1.0"
    assert migrated["steps"][0]["id"] == "thumbnail"
    with pytest.raises(ValidationError, match="no pipeline migration path"):
        migrate_pipeline_document({**source, "schema_version": "0.9"})
    with pytest.raises(ValidationError, match="unsupported target"):
        migrate_pipeline_document(source, "2.0")


def test_pipeline_cancellation_and_dependency_blocking_are_stable(tmp_path):
    pipeline = PipelineCompiler(ffmpeg_path="missing-ffmpeg", ffprobe_path="missing-ffprobe").compile(
        PipelineSpec.from_dict(_document("missing-input.mkv"), base_dir=tmp_path),
        cache_enabled=False,
    )
    cancellation = threading.Event()
    cancellation.set()
    cancelled = PipelineRunner(ffmpeg_path="missing-ffmpeg", ffprobe_path="missing-ffprobe").run(
        pipeline,
        cancellation=cancellation,
    )
    assert [item.status for item in cancelled.items] == ["cancelled", "cancelled"]

    failed = PipelineRunner(ffmpeg_path="missing-ffmpeg", ffprobe_path="missing-ffprobe").run(pipeline)
    assert [item.status for item in failed.items] == ["failed", "blocked"]
    assert failed.items[0].execution.result.exit_category == "environment"
