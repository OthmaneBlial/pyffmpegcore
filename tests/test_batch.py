"""Contracts for bounded, resumable, privacy-aware batch automation."""

from __future__ import annotations

import json
import sys
import threading
import time
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
    assert json.loads(state.read_text())["completed"]["resume"] == BatchJob("resume", plan).signature

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
    document = (receipts / "failed.receipt.json").read_text()
    assert "private-value" not in document
    assert str(tmp_path) not in document
    assert "<path>" in document


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
    document = {
        "schema_version": "1.0",
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
        ],
    }

    manifest = BatchManifest.from_dict(document, base_dir=tmp_path)

    assert manifest.policy.max_input_bytes == 2 * 1024 * 1024
    assert [job.plan.workflow for job in manifest.jobs] == ["convert", "normalize-audio"]
    assert manifest.jobs[1].plan.inputs[0].endswith("source ü.wav")
    assert manifest.to_dict()["schema_version"] == "1.0"


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
