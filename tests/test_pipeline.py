"""Strict schema, DAG, secret, preflight, and migration pipeline contracts."""

from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from pyffmpegcore import (
    PipelineCompiler,
    PipelineEvent,
    PipelineRun,
    PipelineRunner,
    PipelineSpec,
    PipelineStepOutcome,
    PreparedPipeline,
    ValidationError,
    migrate_pipeline_document,
)
from pyffmpegcore.cli import main
from pyffmpegcore.pipeline import _validate_state_destination as _validate_pipeline_state
from pyffmpegcore.pipeline import _write_pipeline_state
from pyffmpegcore.pipeline_compiler import PreparedPipelineStep
from pyffmpegcore.pipeline_runner import _file_fingerprint, _runtime_fingerprint
from pyffmpegcore.preflight import PreflightCheck, PreflightReport

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_pipeline_cache_treats_windows_drive_paths_as_local():
    fingerprint = _file_fingerprint(r"C:\media\sample.mp4", content_aware=False)

    assert "remote" not in fingerprint


def test_pipeline_cache_disables_reuse_when_tool_version_probe_fails(monkeypatch):
    def fail(_runner):
        raise subprocess.CalledProcessError(1, ["ffmpeg", "-version"])

    monkeypatch.setattr("pyffmpegcore.pipeline_runner.FFmpegRunner.get_version", fail)

    assert _runtime_fingerprint("ffmpeg", "ffprobe") is None


def test_documented_powershell_pipeline_uses_environment_and_resume_evidence():
    """Keep the copyable PowerShell flow aligned with the public CLI contract."""
    guide = (REPO_ROOT / "docs" / "pipelines.md").read_text(encoding="utf-8")
    section = guide.split("### PowerShell: variable, evidence, and resume", 1)[1].split(
        "## Optional content-aware cache", 1
    )[0]
    assert '$env:INPUT = (Resolve-Path "tests/media/downloads/sample_video_mov.mov").Path' in section
    assert '$env:OUTPUT_DIR = Join-Path (Get-Location).Path "build/Web Publish"' in section
    assert section.count('pyffmpegcore pipeline run "pipelines/web-publish.json"') == 2
    for token in (
        "--var INPUT --var OUTPUT_DIR",
        '--receipt-dir "build/Pipeline Receipts"',
        '--events "build/Pipeline Events.jsonl"',
        '--state "build/Pipeline State.json"',
        "--resume",
    ):
        assert token in section
    assert "--var INPUT=" not in section


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


def test_pipeline_decodes_percent_escaped_local_file_urls(tmp_path):
    source = tmp_path / "media with spaces.mkv"
    output = tmp_path / "output with spaces.mkv"
    document = {
        "schema_version": "1.0",
        "name": "file_uri",
        "steps": [
            {
                "id": "convert",
                "workflow": "convert",
                "input": source.as_uri(),
                "output": output.as_uri(),
            }
        ],
    }

    pipeline = PipelineCompiler().compile(PipelineSpec.from_dict(document, base_dir=tmp_path))

    assert pipeline.steps[0].plan.inputs == (str(source),)
    assert pipeline.steps[0].plan.outputs == (str(output),)


@pytest.mark.skipif(os.name == "nt", reason="Windows supports file URLs as UNC paths")
def test_pipeline_rejects_remote_file_url_authority(tmp_path):
    document = {
        "schema_version": "1.0",
        "name": "remote_file_uri",
        "steps": [
            {
                "id": "convert",
                "workflow": "convert",
                "input": "file://media.example/source.mkv",
                "output": "result.mkv",
            }
        ],
    }

    with pytest.raises(ValidationError, match="file URLs with a remote host"):
        PipelineCompiler().compile(PipelineSpec.from_dict(document, base_dir=tmp_path))


def test_pipeline_convert_step_can_preserve_every_stream(tmp_path):
    source = tmp_path / "source.mkv"
    source.write_bytes(b"media")
    document = {
        "schema_version": "1.0",
        "name": "preserve_tracks",
        "steps": [
            {
                "id": "remux",
                "workflow": "convert",
                "input": str(source),
                "output": "preserved.mkv",
                "options": {"preserve_all_streams": True},
            }
        ],
    }

    pipeline = PipelineCompiler().compile(PipelineSpec.from_dict(document, base_dir=tmp_path))
    command = pipeline.steps[0].plan.command

    assert command[command.index("-map") + 1] == "0"
    assert command[command.index("-c") + 1] == "copy"
    assert pipeline.steps[0].plan.metadata["stream_policy"] == "preserve-all"


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
    assert pipeline.steps[0].plan.inputs == (secret,)
    rendered = json.dumps(pipeline.to_dict())
    assert "very-private-token" not in rendered
    assert "<redacted>" in rendered

    inline = dict(document)
    inline["variables"] = {"SOURCE_URL": secret}
    with pytest.raises(ValidationError, match="must not have values"):
        PipelineSpec.from_dict(inline, base_dir=tmp_path)


def test_pipeline_secret_is_masked_from_every_public_renderer(tmp_path):
    document = {
        "schema_version": "1.0",
        "name": "private_source",
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
    secret = "https://user:do-not-log@example.invalid/video.mp4?token=do-not-log"
    pipeline = PipelineCompiler().compile(
        PipelineSpec.from_dict(document, base_dir=tmp_path),
        variables={"SOURCE_URL": secret},
    )
    rendered = [
        json.dumps(pipeline.to_dict()),
        pipeline.graph("text"),
        pipeline.graph("mermaid"),
        pipeline.graph("dot"),
        json.dumps(PreparedPipeline(pipeline, ()).to_dict()),
        json.dumps(PipelineEvent(1, "failed", "web", secret).to_dict(pipeline.secret_values)),
        json.dumps(PipelineRun(pipeline, (PipelineStepOutcome("web", "failed", "key", detail=secret),)).to_dict()),
    ]

    assert all("do-not-log" not in value for value in rendered)
    assert sum("<redacted>" in value for value in rendered) >= 3


@pytest.mark.parametrize(
    "mode",
    ["preview", "failure", "validate-json", "plan-json", "preflight-json", "result-json"],
)
def test_pipeline_cli_output_redacts_secret(tmp_path, monkeypatch, capsys, mode):
    secret = "https://user:integration-secret@example.invalid/video.mp4?token=integration-secret"
    pipeline_path = tmp_path / "pipeline.json"
    pipeline_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "name": "private_source",
                "secret_variables": ["SOURCE_URL"],
                "steps": [
                    {
                        "id": "encode",
                        "profile": "web/mp4-compatible",
                        "input": "${SOURCE_URL}",
                        "output": str(tmp_path / "output.mp4"),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SOURCE_URL", secret)

    def prepare(_engine, pipeline, **_kwargs):
        return PreparedPipeline(
            pipeline,
            tuple(
                PreparedPipelineStep(
                    step.id,
                    step.needs,
                    step.plan,
                    PreflightReport(
                        step.plan.workflow,
                        (PreflightCheck("output", "fail", f"blocked by {secret}"),) if mode == "preflight-json" else (),
                    ),
                )
                for step in pipeline.steps
            ),
        )

    monkeypatch.setattr("pyffmpegcore.cli_workflows.PipelinePreflightEngine.prepare", prepare)
    if mode in {"failure", "result-json"}:

        def fail(_runner, pipeline, **_kwargs):
            return PipelineRun(
                pipeline,
                (PipelineStepOutcome("encode", "failed", "cache-key", detail=f"fetch failed: {secret}"),),
            )

        monkeypatch.setattr(PipelineRunner, "run", fail)

    if mode == "preview":
        arguments = ["pipeline", "run", str(pipeline_path), "--var", "SOURCE_URL", "--explain"]
    elif mode == "failure":
        arguments = ["pipeline", "run", str(pipeline_path), "--var", "SOURCE_URL"]
    elif mode == "validate-json":
        arguments = ["pipeline", "validate", str(pipeline_path), "--var", "SOURCE_URL", "--json"]
    elif mode == "plan-json":
        arguments = ["pipeline", "run", str(pipeline_path), "--var", "SOURCE_URL", "--dry-run", "--plan-json"]
    elif mode == "preflight-json":
        arguments = ["pipeline", "run", str(pipeline_path), "--var", "SOURCE_URL", "--result-json"]
    else:
        arguments = ["pipeline", "run", str(pipeline_path), "--var", "SOURCE_URL", "--result-json"]

    result = main(arguments)
    captured = capsys.readouterr()

    assert "integration-secret" not in captured.out + captured.err
    assert "<redacted>" in captured.out + captured.err
    assert (result != 0) if mode in {"failure", "preflight-json", "result-json"} else (result == 0)


def test_pipeline_schema_migration_is_explicit_and_canonical(tmp_path):
    source = _document("source.mkv")
    migrated = migrate_pipeline_document(source)
    assert migrated["schema_version"] == "1.0"
    assert migrated["steps"][0]["id"] == "thumbnail"
    with pytest.raises(ValidationError, match="no pipeline migration path"):
        migrate_pipeline_document({**source, "schema_version": "0.9"})
    with pytest.raises(ValidationError, match="unsupported target"):
        migrate_pipeline_document(source, "2.0")


def test_pipeline_cache_rejects_a_modified_output(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    output = tmp_path / "output.mp4"
    source.write_bytes(b"source media")
    spec = PipelineSpec.from_dict(
        {
            "schema_version": "1.0",
            "name": "cache_integrity",
            "cache": {"enabled": True, "directory": ".cache", "content_aware": True},
            "steps": [{"id": "convert", "workflow": "convert", "input": str(source), "output": str(output)}],
        },
        base_dir=tmp_path,
    )
    pipeline = PipelineCompiler().compile(spec, force=True)
    calls = []

    def fake_run(_engine, plan, **_kwargs):
        calls.append(plan)
        Path(plan.outputs[0]).write_bytes(f"generated-{len(calls)}".encode())
        return SimpleNamespace(items=(SimpleNamespace(succeeded=True),))

    monkeypatch.setattr("pyffmpegcore.pipeline.WorkflowEngine.run", fake_run)
    runner = PipelineRunner()

    first = runner.run(pipeline)
    second = runner.run(pipeline)
    assert first.items[0].status == "succeeded"
    assert second.items[0].status == "cached"
    assert len(calls) == 1

    output.write_bytes(b"tampered output")
    third = runner.run(pipeline)

    assert third.items[0].status == "succeeded"
    assert len(calls) == 2
    assert output.read_bytes() == b"generated-2"


def test_pipeline_cache_invalidates_when_ffmpeg_version_changes(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    output = tmp_path / "output.mp4"
    source.write_bytes(b"source media")
    spec = PipelineSpec.from_dict(
        {
            "schema_version": "1.0",
            "name": "cache_runtime",
            "cache": {"enabled": True, "directory": ".cache", "content_aware": True},
            "steps": [{"id": "convert", "workflow": "convert", "input": str(source), "output": str(output)}],
        },
        base_dir=tmp_path,
    )
    pipeline = PipelineCompiler().compile(spec, force=True)
    version = ["ffmpeg build one"]
    calls = []
    monkeypatch.setattr(
        "pyffmpegcore.pipeline_runner._runtime_fingerprint",
        lambda *_args: {"pyffmpegcore": "test", "ffmpeg": version[0], "ffprobe": "ffprobe build"},
    )

    def fake_run(_engine, plan, **_kwargs):
        calls.append(plan)
        Path(plan.outputs[0]).write_bytes(f"generated-{len(calls)}".encode())
        return SimpleNamespace(items=(SimpleNamespace(succeeded=True),))

    monkeypatch.setattr("pyffmpegcore.pipeline.WorkflowEngine.run", fake_run)
    runner = PipelineRunner()
    assert runner.run(pipeline).items[0].status == "succeeded"
    assert runner.run(pipeline).items[0].status == "cached"

    version[0] = "ffmpeg build two"
    assert runner.run(pipeline).items[0].status == "succeeded"
    assert len(calls) == 2


def test_pipeline_cache_does_not_reuse_remote_inputs(tmp_path, monkeypatch):
    output = tmp_path / "output.mp4"
    spec = PipelineSpec.from_dict(
        {
            "schema_version": "1.0",
            "name": "cache_remote",
            "cache": {"enabled": True, "directory": ".cache", "content_aware": True},
            "steps": [
                {
                    "id": "convert",
                    "workflow": "convert",
                    "input": "https://media.example/video.mp4",
                    "output": str(output),
                }
            ],
        },
        base_dir=tmp_path,
    )
    pipeline = PipelineCompiler().compile(spec, force=True)
    monkeypatch.setattr(
        "pyffmpegcore.pipeline_runner._runtime_fingerprint",
        lambda *_args: {"pyffmpegcore": "test", "ffmpeg": "ffmpeg build", "ffprobe": "ffprobe build"},
    )
    calls = []

    def fake_run(_engine, plan, **_kwargs):
        calls.append(plan)
        Path(plan.outputs[0]).write_bytes(f"generated-{len(calls)}".encode())
        return SimpleNamespace(items=(SimpleNamespace(succeeded=True),))

    monkeypatch.setattr("pyffmpegcore.pipeline.WorkflowEngine.run", fake_run)
    runner = PipelineRunner()

    assert runner.run(pipeline).items[0].status == "succeeded"
    assert runner.run(pipeline).items[0].status == "succeeded"
    assert len(calls) == 2


def test_cli_pipeline_migrate_rejects_dangling_output_symlink(tmp_path, capsys):
    source = tmp_path / "pipeline.json"
    source.write_text(json.dumps(_document("source.mp4")), encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "migrated.json"
    link = tmp_path / "migrated.json"
    link.symlink_to(target)

    assert main(["pipeline", "migrate", str(source), str(link)]) == 4
    assert "Pipeline output already exists" in capsys.readouterr().err
    assert not target.exists()


def test_cli_pipeline_migrate_preserves_output_created_after_preflight(tmp_path, capsys, monkeypatch):
    source = tmp_path / "pipeline.json"
    source.write_text(json.dumps(_document("source.mp4")), encoding="utf-8")
    output = tmp_path / "migrated.json"

    def create_competing_output(_document, *_args):
        output.write_text("concurrent writer", encoding="utf-8")
        return _document

    monkeypatch.setattr("pyffmpegcore.cli_workflows.migrate_pipeline_document", create_competing_output)

    assert main(["pipeline", "migrate", str(source), str(output)]) == 4
    assert "Pipeline output already exists" in capsys.readouterr().err
    assert output.read_text(encoding="utf-8") == "concurrent writer"


def test_cli_pipeline_migrate_reports_parent_path_errors(tmp_path, capsys):
    source = tmp_path / "pipeline.json"
    source.write_text(json.dumps(_document("source.mp4")), encoding="utf-8")
    parent = tmp_path / "not-a-directory"
    parent.write_text("block parent creation", encoding="utf-8")

    assert main(["pipeline", "migrate", str(source), str(parent / "migrated.json")]) == 5
    assert "Unable to write migrated pipeline" in capsys.readouterr().err


def test_pipeline_rejects_receipt_path_that_would_overwrite_media_output(tmp_path, monkeypatch):
    receipt_dir = tmp_path / "receipts"
    document = {
        "schema_version": "1.0",
        "name": "receipt_collision",
        "steps": [
            {
                "id": "web",
                "workflow": "convert",
                "input": "source.mp4",
                "output": str(receipt_dir / "web.receipt.json"),
            }
        ],
    }
    pipeline = PipelineCompiler().compile(PipelineSpec.from_dict(document, base_dir=tmp_path))
    calls = []
    monkeypatch.setattr("pyffmpegcore.pipeline.WorkflowEngine.run", lambda *_args, **_kwargs: calls.append(True))

    with pytest.raises(ValidationError, match="receipt path collides with a media output"):
        PipelineRunner().run(pipeline, receipt_dir=receipt_dir)

    assert calls == []
    assert not (receipt_dir / "web.receipt.json").exists()


def test_pipeline_rejects_state_path_that_would_overwrite_media_output(tmp_path, monkeypatch):
    state = tmp_path / "pipeline-state.json"
    document = {
        "schema_version": "1.0",
        "name": "state_collision",
        "steps": [
            {
                "id": "web",
                "workflow": "convert",
                "input": "source.mp4",
                "output": str(state),
            }
        ],
    }
    pipeline = PipelineCompiler().compile(PipelineSpec.from_dict(document, base_dir=tmp_path))
    calls = []
    monkeypatch.setattr("pyffmpegcore.pipeline.WorkflowEngine.run", lambda *_args, **_kwargs: calls.append(True))

    with pytest.raises(ValidationError, match="state path collides with a media output"):
        PipelineRunner().run(pipeline, state_path=state)

    assert calls == []
    assert not state.exists()


def test_pipeline_preserves_existing_state_without_explicit_resume_or_overwrite(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    state = tmp_path / "state.json"
    state.write_text("preserve", encoding="utf-8")
    pipeline = PipelineCompiler().compile(PipelineSpec.from_dict(_document(str(source)), base_dir=tmp_path))
    calls = []
    monkeypatch.setattr("pyffmpegcore.pipeline.WorkflowEngine.run", lambda *_args, **_kwargs: calls.append(True))

    with pytest.raises(ValidationError, match="state file already exists"):
        PipelineRunner().run(pipeline, state_path=state)

    assert calls == []
    assert state.read_text(encoding="utf-8") == "preserve"


def test_pipeline_does_not_overwrite_state_created_after_preflight(tmp_path, monkeypatch):
    state = tmp_path / "racing-state.json"
    pipeline = PipelineCompiler().compile(
        PipelineSpec.from_dict(_document("source.mp4"), base_dir=tmp_path),
        cache_enabled=False,
    )
    calls = []

    def create_racing_file(*args, **kwargs):
        _validate_pipeline_state(*args, **kwargs)
        state.write_text("created concurrently", encoding="utf-8")

    def fake_run(*_args, **_kwargs):
        calls.append(True)
        raise AssertionError("pipeline started before claiming its state path")

    monkeypatch.setattr("pyffmpegcore.pipeline_runner._validate_state_destination", create_racing_file)
    monkeypatch.setattr("pyffmpegcore.pipeline.WorkflowEngine.run", fake_run)

    with pytest.raises(ValidationError, match="state file already exists"):
        PipelineRunner().run(pipeline, state_path=state)

    assert calls == []
    assert state.read_text(encoding="utf-8") == "created concurrently"


def test_pipeline_reports_state_parent_path_errors(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    parent = tmp_path / "not-a-directory"
    parent.write_text("block parent creation", encoding="utf-8")
    pipeline = PipelineCompiler().compile(PipelineSpec.from_dict(_document(str(source)), base_dir=tmp_path))

    with pytest.raises(ValidationError, match="unable to create state file"):
        PipelineRunner().run(pipeline, state_path=parent / "state.json")


def test_pipeline_state_write_preserves_preexisting_temp_name(tmp_path):
    state = tmp_path / "state.json"
    old_temp = tmp_path / ".state.json.tmp"
    old_temp.write_text("preserve", encoding="utf-8")

    _write_pipeline_state(state, {"web": "signature"})

    assert json.loads(state.read_text(encoding="utf-8"))["schema_version"] == "1.0"
    assert old_temp.read_text(encoding="utf-8") == "preserve"


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
