"""Privacy and compatibility contracts for run receipts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyffmpegcore import (
    ExecutionPlan,
    JobResult,
    JobStatus,
    PreflightReport,
    PreparedWorkflow,
    ReceiptBuilder,
    RunReceipt,
    ValidationError,
    WorkflowBatch,
    WorkflowExecution,
    migrate_receipt,
    validate_receipt,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _batch(tmp_path):
    source = tmp_path / "private-project" / "source.bin"
    source.parent.mkdir()
    source.write_bytes(b"receipt input")
    output = tmp_path / "secret-customer" / "output.bin"
    output.parent.mkdir()
    output.write_bytes(b"receipt output")
    remote = "https://alice:supersecret@example.test/media/video.mp4?token=query-secret"
    plan = ExecutionPlan(
        workflow="test/receipt",
        command=(
            "ffmpeg",
            "-headers",
            "Authorization: Bearer header-secret",
            "-i",
            remote,
            str(output),
        ),
        inputs=(remote, str(source)),
        outputs=(str(output),),
        metadata={"api_key": "metadata-secret", "nested": f"token=inline-secret path={source}"},
    )
    report = PreflightReport(plan.workflow, ())
    result = JobResult(
        workflow=plan.workflow,
        command=plan.command,
        status=JobStatus.SUCCEEDED,
        exit_category="ok",
        returncode=0,
        elapsed_seconds=1.25,
        outputs=({"path": str(output), "exists": True, "size_bytes": output.stat().st_size},),
    )
    execution = WorkflowExecution(remote, str(output), report, result)
    return WorkflowBatch(PreparedWorkflow(plan, report), (execution,)), source, output


def test_receipt_redacts_credentials_private_paths_and_secrets_by_default(tmp_path):
    batch, source, _output = _batch(tmp_path)

    receipt = ReceiptBuilder(ffmpeg_path="missing-ffmpeg", ffprobe_path="missing-ffprobe").build(batch)
    rendered = receipt.to_json()

    assert validate_receipt(receipt.to_dict()) == ()
    assert "alice" not in rendered
    assert "supersecret" not in rendered
    assert "query-secret" not in rendered
    assert "header-secret" not in rendered
    assert "metadata-secret" not in rendered
    assert "inline-secret" not in rendered
    assert str(source.parent) not in rendered
    assert "<path>/source.bin" in rendered
    assert receipt.document["privacy"]["content_hashing"] == "disabled"
    assert receipt.document["content_hashes"] == []


def test_receipt_hashing_is_opt_in_and_records_algorithm(tmp_path):
    batch, source, _output = _batch(tmp_path)

    receipt = ReceiptBuilder(ffmpeg_path="missing-ffmpeg", ffprobe_path="missing-ffprobe").build(
        batch, hash_content=True
    )

    source_hash = next(item for item in receipt.document["content_hashes"] if item["path"].endswith("source.bin"))
    assert source_hash["algorithm"] == "sha256"
    assert len(source_hash["digest"]) == 64
    assert str(source.parent) not in receipt.to_json()


def test_receipt_round_trip_and_validation_errors(tmp_path):
    batch, _source, _output = _batch(tmp_path)
    receipt = ReceiptBuilder(ffmpeg_path="missing-ffmpeg", ffprobe_path="missing-ffprobe").build(batch)
    path = receipt.write(tmp_path / "receipts" / "run.json")

    assert RunReceipt.read(path).to_dict() == receipt.to_dict()
    broken = json.loads(receipt.to_json())
    broken["schema_version"] = "99"
    assert validate_receipt(broken) == ("schema_version must be '1.0'",)
    with pytest.raises(ValidationError, match="invalid receipt"):
        RunReceipt(broken)
    with pytest.raises(ValidationError, match="no receipt migration path"):
        migrate_receipt(broken)
    assert migrate_receipt(receipt.to_dict()).to_dict() == receipt.to_dict()


def test_published_receipt_example_matches_runtime_validator():
    example = json.loads((REPO_ROOT / "docs" / "schemas" / "run-receipt-1.0.example.json").read_text(encoding="utf-8"))

    assert validate_receipt(example) == ()
