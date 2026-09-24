"""Contracts for bounded, resumable, privacy-aware batch automation."""

from __future__ import annotations

import json
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

from pyffmpegcore import (
    BatchEvent,
    BatchJob,
    BatchManifest,
    BatchPolicy,
    BatchRunner,
    ExecutionPlan,
    JobResult,
    JobStatus,
    ValidationError,
)
from pyffmpegcore.batch import _validate_state_destination as _validate_batch_state_destination
from pyffmpegcore.preflight import PreflightCheck, PreflightReport
from pyffmpegcore.workflow import PreparedWorkflow, WorkflowBatch, WorkflowExecution


def _plan(tmp_path: Path, name: str) -> ExecutionPlan:
    source = tmp_path / f"{name} input's ünicode.mp4"
    source.write_bytes(name.encode())
    return ExecutionPlan(
        workflow=f"test/{name}",
        command=(sys.executable, "-c", "pass"),
        inputs=(str(source),),
        outputs=(str(tmp_path / f"{name}.mp4"),),
    )


class FakeEngine:
    def __init__(self, responses=None, delay: float = 0.0):
        self.responses = responses or {}
        self.delay = delay
        self.calls: list[str] = []
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def prepare(self, plan):
        return PreparedWorkflow(plan, PreflightReport(plan.workflow, (PreflightCheck("fake", "pass", "ok"),)))

    def run(self, plan, *, cancellation=None):
        with self.lock:
            self.calls.append(plan.workflow)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            configured = self.responses.get(plan.workflow, [(JobStatus.SUCCEEDED, "success", "")])
            status, category, diagnostic = configured.pop(0)
        try:
            if self.delay:
                time.sleep(self.delay)
            if status is JobStatus.SUCCEEDED:
                Path(plan.outputs[0]).write_bytes(b"complete")
            report = PreflightReport(plan.workflow, (PreflightCheck("fake", "pass", "ok"),))
            result = JobResult(
                workflow=plan.workflow,
                command=plan.command,
                status=status,
                exit_category=category,
                returncode=0 if status is JobStatus.SUCCEEDED else 1,
                elapsed_seconds=self.delay,
                stderr=diagnostic,
            )
            execution = WorkflowExecution(plan.inputs[0], plan.outputs[0], report, result)
            return WorkflowBatch(PreparedWorkflow(plan, report), (execution,))
        finally:
            with self.lock:
                self.active -= 1


def test_batch_is_bounded_emits_ordered_events_and_keeps_ordered_results(tmp_path):
    engine = FakeEngine(delay=0.03)
    jobs = tuple(BatchJob(f"job-{index}", _plan(tmp_path, str(index))) for index in range(5))
    events: list[BatchEvent] = []

    result = BatchRunner(engine=engine).run(
        jobs,
        policy=BatchPolicy(max_workers=2),
        event_callback=events.append,
    )

    assert result.succeeded
    assert engine.max_active == 2
    assert [item.job_id for item in result.items] == [job.id for job in jobs]
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    assert {event.event for event in events} >= {"queued", "started", "succeeded"}


def test_batch_retries_only_classified_transient_runtime_failures(tmp_path):
    transient = _plan(tmp_path, "transient")
    deterministic = _plan(tmp_path, "deterministic")
    engine = FakeEngine(
        {
            transient.workflow: [
                (JobStatus.FAILED, "runtime", "HTTP error 503"),
                (JobStatus.SUCCEEDED, "success", ""),
            ],
            deterministic.workflow: [(JobStatus.FAILED, "validation", "unsupported capability")],
        }
    )

    result = BatchRunner(engine=engine).run(
        (BatchJob("transient", transient), BatchJob("deterministic", deterministic)),
        policy=BatchPolicy(max_workers=1, max_retries=3),
    )

    assert result.items[0].status == "succeeded"
    assert result.items[0].attempts == 2
    assert result.items[1].status == "failed"
    assert result.items[1].attempts == 1
    assert engine.calls.count(deterministic.workflow) == 1


def test_batch_resume_uses_matching_signature_and_existing_output(tmp_path):
    state = tmp_path / "resume state.json"
    plan = _plan(tmp_path, "resume")
    first_engine = FakeEngine()
    first = BatchRunner(engine=first_engine).run(
        (BatchJob("resume", plan),),
        state_path=state,
    )
    assert first.succeeded
    assert json.loads(state.read_text(encoding="utf-8"))["completed"]["resume"] == BatchJob("resume", plan).signature

    second_engine = FakeEngine()
    second = BatchRunner(engine=second_engine).run(
        (BatchJob("resume", plan),),
        state_path=state,
        resume=True,
    )
    assert second.items[0].status == "resumed"
    assert second.items[0].attempts == 0
    assert second_engine.calls == []


def test_batch_writes_a_redacted_receipt_for_failed_items(tmp_path):
    plan = _plan(tmp_path, "failed")
    engine = FakeEngine({plan.workflow: [(JobStatus.FAILED, "runtime", "token=private-value")]})
    receipts = tmp_path / "receipts"

    result = BatchRunner(engine=engine, ffmpeg_path="missing", ffprobe_path="missing").run(
        (BatchJob("failed", plan),),
        receipt_dir=receipts,
    )

    assert result.items[0].status == "failed"
    document = (receipts / "failed.receipt.json").read_text(encoding="utf-8")
    assert "private-value" not in document
    assert str(tmp_path) not in document
    assert "<path>" in document


def test_batch_rejects_receipt_paths_that_would_overwrite_media_outputs(tmp_path):
    receipt_dir = tmp_path / "receipts"
    output = receipt_dir / "collision.receipt.json"
    plan = ExecutionPlan(
        workflow="test/receipt-collision",
        command=(sys.executable, "-c", "pass"),
        inputs=(),
        outputs=(str(output),),
    )
    engine = FakeEngine()

    with pytest.raises(ValidationError, match="receipt path collides with a media output"):
        BatchRunner(engine=engine).run((BatchJob("collision", plan),), receipt_dir=receipt_dir)

    assert engine.calls == []
    assert not output.exists()


def test_batch_rejects_existing_receipt_before_running_jobs(tmp_path):
    plan = _plan(tmp_path, "existing-receipt")
    receipt_dir = tmp_path / "receipts"
    receipt_dir.mkdir()
    receipt = receipt_dir / "existing-receipt.receipt.json"
    receipt.write_text("preserve", encoding="utf-8")
    engine = FakeEngine()

    with pytest.raises(ValidationError, match="receipt already exists"):
        BatchRunner(engine=engine).run((BatchJob("existing-receipt", plan),), receipt_dir=receipt_dir)

    assert engine.calls == []
    assert receipt.read_text(encoding="utf-8") == "preserve"


def test_batch_can_explicitly_replace_existing_receipt(tmp_path):
    plan = _plan(tmp_path, "replace-receipt")
    receipt_dir = tmp_path / "receipts"
    receipt_dir.mkdir()
    receipt = receipt_dir / "replace-receipt.receipt.json"
    receipt.write_text("old receipt", encoding="utf-8")

    result = BatchRunner(engine=FakeEngine(), ffmpeg_path="missing", ffprobe_path="missing").run(
        (BatchJob("replace-receipt", plan),),
        receipt_dir=receipt_dir,
        overwrite_receipts=True,
    )

    assert result.succeeded
    assert json.loads(receipt.read_text(encoding="utf-8"))["schema_version"] == "1.0"


def test_batch_rejects_state_path_that_would_overwrite_media_output(tmp_path):
    state = tmp_path / "state.json"
    plan = replace(_plan(tmp_path, "state-collision"), outputs=(str(state),))
    engine = FakeEngine()

    with pytest.raises(ValidationError, match="state path collides with a media output"):
        BatchRunner(engine=engine).run((BatchJob("state-collision", plan),), state_path=state)

    assert engine.calls == []
    assert not state.exists()


def test_batch_rejects_state_path_that_would_overwrite_a_receipt(tmp_path):
    receipt_dir = tmp_path / "receipts"
    state = receipt_dir / "state-collision.receipt.json"
    engine = FakeEngine()

    with pytest.raises(ValidationError, match="state path collides with a receipt"):
        BatchRunner(engine=engine).run(
            (BatchJob("state-collision", _plan(tmp_path, "state-receipt-collision")),),
            state_path=state,
            receipt_dir=receipt_dir,
        )

    assert engine.calls == []
    assert not receipt_dir.exists()


def test_batch_preserves_existing_state_unless_resume_or_overwrite_is_explicit(tmp_path):
    state = tmp_path / "existing-state.json"
    state.write_text("preserve", encoding="utf-8")
    job = BatchJob("state-overwrite", _plan(tmp_path, "state-overwrite"))
    engine = FakeEngine()

    with pytest.raises(ValidationError, match="state file already exists"):
        BatchRunner(engine=engine).run((job,), state_path=state)

    assert engine.calls == []
    assert state.read_text(encoding="utf-8") == "preserve"

    result = BatchRunner(engine=engine).run((job,), state_path=state, overwrite_state=True)
    assert result.succeeded
    assert json.loads(state.read_text(encoding="utf-8"))["schema_version"] == "1.0"


def test_batch_does_not_overwrite_state_created_after_preflight(tmp_path, monkeypatch):
    state = tmp_path / "racing-state.json"

    def create_racing_file(*args, **kwargs):
        _validate_batch_state_destination(*args, **kwargs)
        state.write_text("created concurrently", encoding="utf-8")

    monkeypatch.setattr("pyffmpegcore.batch._validate_state_destination", create_racing_file)
    engine = FakeEngine()

    with pytest.raises(ValidationError, match="state file already exists"):
        BatchRunner(engine=engine).run(
            (BatchJob("state-race", _plan(tmp_path, "state-race")),),
            state_path=state,
        )

    assert engine.calls == []
    assert state.read_text(encoding="utf-8") == "created concurrently"


def test_batch_reports_state_parent_path_errors(tmp_path):
    parent = tmp_path / "not-a-directory"
    parent.write_text("block parent creation", encoding="utf-8")
    job = BatchJob("invalid-state-path", _plan(tmp_path, "invalid-state-path"))

    with pytest.raises(ValidationError, match="unable to create state file"):
        BatchRunner(engine=FakeEngine()).run((job,), state_path=parent / "state.json")


def test_batch_state_write_preserves_preexisting_temp_name(tmp_path):
    state = tmp_path / "state.json"
    old_temp = tmp_path / ".state.json.tmp"
    old_temp.write_text("preserve", encoding="utf-8")
    job = BatchJob("atomic-state", _plan(tmp_path, "atomic-state"))

    result = BatchRunner(engine=FakeEngine()).run((job,), state_path=state)

    assert result.succeeded
    assert json.loads(state.read_text(encoding="utf-8"))["schema_version"] == "1.0"
    assert old_temp.read_text(encoding="utf-8") == "preserve"


def test_batch_rejects_duplicate_work_collisions_and_resource_overruns(tmp_path):
    first = _plan(tmp_path, "first")
    duplicate = BatchJob("duplicate", first)
    with pytest.raises(ValidationError, match="duplicate batch work"):
        BatchRunner(engine=FakeEngine()).run((BatchJob("first", first), duplicate))

    second = _plan(tmp_path, "second")
    colliding = ExecutionPlan(
        workflow=second.workflow,
        command=second.command,
        inputs=second.inputs,
        outputs=(first.outputs[0].upper(),),
    )
    with pytest.raises(ValidationError, match="output collision"):
        BatchRunner(engine=FakeEngine()).run((BatchJob("first", first), BatchJob("second", colliding)))

    with pytest.raises(ValidationError, match="exceeds max_input_bytes"):
        BatchRunner(engine=FakeEngine()).run(
            (BatchJob("first", first),),
            policy=BatchPolicy(max_input_bytes=1),
        )


def test_batch_manifest_compiles_mixed_profiles_relative_to_itself(tmp_path):
    (tmp_path / "clips").mkdir()
    (tmp_path / "clips" / "source ü.wav").write_bytes(b"audio")
    (tmp_path / "clips" / "source.mp4").write_bytes(b"video")
    (tmp_path / "clips" / "captions.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nBonjour\n", encoding="utf-8")
    document = {
        "schema_version": "1.1",
        "policy": {"max_workers": 2, "max_retries": 1, "max_input_bytes": "2MiB"},
        "jobs": [
            {
                "id": "web",
                "profile": "web/mp4-compatible",
                "input": "clips/source.mp4",
                "output": "out/web.mp4",
            },
            {
                "id": "podcast",
                "profile": "audio/podcast-speech",
                "input": "clips/source ü.wav",
                "output": "out/podcast.m4a",
            },
            {
                "id": "captioned",
                "profile": "subtitles/accessibility",
                "input": "clips/source.mp4",
                "output": "out/captioned.mp4",
                "subtitle": "clips/captions.srt",
                "subtitle_language": "fra",
            },
        ],
    }

    manifest = BatchManifest.from_dict(document, base_dir=tmp_path)

    assert manifest.policy.max_input_bytes == 2 * 1024 * 1024
    assert [job.plan.workflow for job in manifest.jobs] == ["convert", "normalize-audio", "subtitles/add"]
    assert manifest.jobs[1].plan.inputs[0].endswith("source ü.wav")
    assert "language=fra" in manifest.jobs[2].plan.command
    assert manifest.to_dict()["schema_version"] == "1.1"


def test_batch_manifest_preserves_1_0_and_rejects_1_1_fields(tmp_path):
    document = {
        "schema_version": "1.0",
        "jobs": [{"id": "web", "profile": "web/mp4-compatible", "input": "source.mov", "output": "out.mp4"}],
    }

    manifest = BatchManifest.from_dict(document, base_dir=tmp_path)

    assert manifest.to_dict()["schema_version"] == "1.0"
    document["jobs"][0]["subtitle_language"] = "fra"
    with pytest.raises(ValidationError, match="requires batch manifest schema_version '1.1'"):
        BatchManifest.from_dict(document, base_dir=tmp_path)


@pytest.mark.parametrize("language", [None, "", 42])
def test_batch_manifest_rejects_invalid_subtitle_language(tmp_path, language):
    document = {
        "schema_version": "1.1",
        "jobs": [
            {
                "id": "captioned",
                "profile": "subtitles/accessibility",
                "input": "source.mp4",
                "output": "captioned.mp4",
                "subtitle": "captions.srt",
                "subtitle_language": language,
            }
        ],
    }

    with pytest.raises(ValidationError, match="subtitle_language must be a non-empty string"):
        BatchManifest.from_dict(document, base_dir=tmp_path)


def test_cancelled_batch_does_not_start_work(tmp_path):
    cancellation = threading.Event()
    cancellation.set()
    engine = FakeEngine()

    result = BatchRunner(engine=engine).run(
        (BatchJob("cancelled", _plan(tmp_path, "cancelled")),),
        cancellation=cancellation,
    )

    assert result.items[0].status == "cancelled"
    assert engine.calls == []
