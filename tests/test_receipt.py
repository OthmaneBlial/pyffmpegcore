"""Privacy and compatibility contracts for run receipts."""

from __future__ import annotations

import json
import os
import stat
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

import pytest

from pyffmpegcore import (
    ExecutionPlan,
    JobResult,
    JobStatus,
    PreflightCheck,
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
from pyffmpegcore.receipt import _version_line, redact_receipt_value

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
    report = PreflightReport(
        plan.workflow,
        (
            PreflightCheck(
                f"output/{output}",
                "pass",
                f"Output parent is writable: {output.parent}",
            ),
        ),
    )
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


@patch("pyffmpegcore.receipt.subprocess.run")
def test_receipt_version_probe_decodes_tool_output_as_utf8(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(["ffmpeg", "-version"], 0, "ffmpeg version 9.0\n", "")

    assert _version_line("ffmpeg") == "ffmpeg version 9.0"
    assert mock_run.call_args.kwargs["encoding"] == "utf-8"
    assert mock_run.call_args.kwargs["errors"] == "replace"


def test_receipt_redacts_credentials_private_paths_and_secrets_by_default(tmp_path):
    batch, source, output = _batch(tmp_path)

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
    assert str(output.parent) not in rendered
    assert "Output parent is writable: <path>" in rendered
    assert "<path>/source.bin" in rendered
    assert receipt.document["privacy"]["content_hashing"] == "disabled"
    assert receipt.document["content_hashes"] == []
    assert receipt.document["items"][0]["proof"]["input_size_bytes"] is None
    assert receipt.document["items"][0]["proof"]["output_size_bytes"] == len(b"receipt output")


def test_receipt_reuses_managed_output_probe_evidence(tmp_path, monkeypatch):
    batch, _source, output = _batch(tmp_path)
    verification = {
        "status": "probed",
        "format_name": "matroska",
        "duration": 2.0,
        "size_bytes": output.stat().st_size,
        "bit_rate": 56,
        "streams": [
            {
                "index": 0,
                "type": "audio",
                "codec": "aac",
                "width": None,
                "height": None,
                "sample_rate": 44100,
                "channels": 2,
                "language": "eng",
                "rotation": None,
            }
        ],
        "chapter_count": 0,
        "stream_preservation": {
            "status": "verified",
            "input_streams": [{"type": "audio", "codec": "aac", "language": "eng"}],
            "output_streams": [{"type": "audio", "codec": "aac", "language": "eng"}],
        },
    }
    item = batch.items[0]
    result = replace(item.result, outputs=(dict(item.result.outputs[0], verification=verification),))
    batch = replace(batch, items=(replace(item, result=result),))

    def unexpected_probe(*_args, **_kwargs):
        raise AssertionError("receipt should reuse the managed output probe")

    monkeypatch.setattr("pyffmpegcore.receipt.FFprobeRunner.probe_media", unexpected_probe)
    receipt = ReceiptBuilder(ffmpeg_path="missing-ffmpeg", ffprobe_path="missing-ffprobe").build(batch)

    output_probe = receipt.document["items"][0]["output_probe"]
    assert output_probe["format_name"] == "matroska"
    assert output_probe["streams"][0]["codec"] == "aac"
    assert output_probe["streams"][0]["language"] == "eng"
    assert output_probe["stream_preservation"]["status"] == "verified"


def test_receipt_keeps_output_probe_facts_when_profile_contract_fails(tmp_path, monkeypatch):
    batch, _source, output = _batch(tmp_path)
    verification = {
        "status": "failed",
        "format_name": "mp4",
        "duration": 2.0,
        "size_bytes": output.stat().st_size,
        "bit_rate": 56,
        "streams": [{"index": 0, "type": "video", "codec": "hevc"}],
        "chapter_count": 0,
        "reason": "expected h264 video, found hevc",
    }
    item = batch.items[0]
    result = replace(item.result, outputs=(dict(item.result.outputs[0], verification=verification),))
    batch = replace(batch, items=(replace(item, result=result),))

    def unexpected_probe(*_args, **_kwargs):
        raise AssertionError("receipt should reuse the failed managed output probe")

    monkeypatch.setattr("pyffmpegcore.receipt.FFprobeRunner.probe_media", unexpected_probe)
    receipt = ReceiptBuilder(ffmpeg_path="missing-ffmpeg", ffprobe_path="missing-ffprobe").build(batch)

    output_probe = receipt.document["items"][0]["output_probe"]
    assert output_probe["format_name"] == "mp4"
    assert output_probe["streams"][0]["codec"] == "hevc"
    assert output_probe["reason"] == "expected h264 video, found hevc"


def test_embedded_media_url_in_ffmpeg_diagnostic_is_redacted():
    secret = "do-not-log"
    diagnostic = (
        "Input #0, mov, from 'https://alice:do-not-log@example.test/private/video.mp4?token=do-not-log': "
        "Bearer do-not-log"
    )

    redacted = redact_receipt_value(diagnostic)

    assert secret not in redacted
    assert "alice" not in redacted
    assert "example.test" in redacted
    assert "<redacted>" in redacted


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


def test_receipt_write_refuses_existing_file_unless_overwrite_is_explicit(tmp_path):
    batch, _source, _output = _batch(tmp_path)
    receipt = ReceiptBuilder(ffmpeg_path="missing-ffmpeg", ffprobe_path="missing-ffprobe").build(batch)
    path = tmp_path / "receipts" / "run.json"
    path.parent.mkdir()
    path.write_text("keep this receipt", encoding="utf-8")

    with pytest.raises(FileExistsError):
        receipt.write(path)
    assert path.read_text(encoding="utf-8") == "keep this receipt"

    assert receipt.write(path, overwrite=True) == path
    assert json.loads(path.read_text(encoding="utf-8")) == receipt.to_dict()


def test_receipt_write_race_never_overwrites_without_permission(tmp_path):
    batch, _source, _output = _batch(tmp_path)
    receipt = ReceiptBuilder(ffmpeg_path="missing-ffmpeg", ffprobe_path="missing-ffprobe").build(batch)
    path = tmp_path / "receipts" / "racing.json"
    barrier = Barrier(2)

    def create_receipt(_index):
        barrier.wait()
        try:
            receipt.write(path)
        except FileExistsError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(create_receipt, range(2)))

    assert sorted(results) == [False, True]
    assert RunReceipt.read(path).to_dict() == receipt.to_dict()


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permission contract")
def test_receipt_files_are_owner_only_with_or_without_overwrite(tmp_path):
    batch, _source, _output = _batch(tmp_path)
    receipt = ReceiptBuilder(ffmpeg_path="missing-ffmpeg", ffprobe_path="missing-ffprobe").build(batch)
    path = receipt.write(tmp_path / "private" / "run.json")

    assert stat.S_IMODE(path.stat().st_mode) & 0o077 == 0
    receipt.write(path, overwrite=True)
    assert stat.S_IMODE(path.stat().st_mode) & 0o077 == 0


def test_published_receipt_example_matches_runtime_validator():
    example = json.loads((REPO_ROOT / "docs" / "schemas" / "run-receipt-1.0.example.json").read_text(encoding="utf-8"))

    assert validate_receipt(example) == ()


def test_receipt_invalid_utf8_is_a_validation_error(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    path.write_bytes(b'{"schema_version":"1.0","items":\xff}')
    with pytest.raises(ValidationError, match="unable to read receipt"):
        RunReceipt.read(path)
