"""Contracts for typed plans, policies, results, and execution."""

from __future__ import annotations

import sys
import threading

import pytest

from pyffmpegcore import (
    CompressOptions,
    ExecutionPlan,
    ExecutionPolicy,
    FFmpegRunner,
    JobStatus,
    OverwritePolicy,
    ValidationError,
)


def test_plan_serialization_uses_stable_string_policies(tmp_path):
    plan = ExecutionPlan(
        workflow="test/noop",
        command=(sys.executable, "-c", "print('ok')"),
        inputs=(),
        outputs=(str(tmp_path / "out.txt"),),
        policy=ExecutionPolicy(overwrite=OverwritePolicy.REPLACE, timeout_seconds=2),
    )

    payload = plan.to_dict()

    assert payload["schema_version"] == "1.0"
    assert payload["policy"]["overwrite"] == "replace"
    assert payload["command"] == (sys.executable, "-c", "print('ok')")


def test_typed_options_reject_invalid_values_immediately():
    with pytest.raises(ValidationError, match="target_size_bytes must be positive"):
        CompressOptions(target_size_bytes=0)

    with pytest.raises(ValidationError, match="timeout_seconds must be positive"):
        ExecutionPolicy(timeout_seconds=0)


def test_execution_plan_returns_stable_result(tmp_path):
    output = tmp_path / "result.txt"
    code = f"from pathlib import Path; Path({str(output)!r}).write_text('done')"
    plan = ExecutionPlan(
        workflow="test/write",
        command=(sys.executable, "-c", code),
        inputs=(),
        outputs=(str(output),),
    )

    result = FFmpegRunner().execute_plan(plan)

    assert result.status is JobStatus.SUCCEEDED
    assert result.exit_category == "ok"
    assert result.returncode == 0
    assert result.elapsed_seconds >= 0
    assert result.outputs[0]["size_bytes"] == 4
    assert result.to_dict()["status"] == "succeeded"


def test_execution_policy_refuses_existing_outputs(tmp_path):
    output = tmp_path / "existing.txt"
    output.write_text("keep", encoding="utf-8")
    plan = ExecutionPlan(
        workflow="test/collision",
        command=(sys.executable, "-c", "raise SystemExit(99)"),
        inputs=(),
        outputs=(str(output),),
    )

    result = FFmpegRunner().execute_plan(plan)

    assert result.status is JobStatus.FAILED
    assert result.exit_category == "validation"
    assert result.returncode is None
    assert output.read_text(encoding="utf-8") == "keep"


def test_execution_policy_supports_timeout_and_cancellation():
    timeout_plan = ExecutionPlan(
        workflow="test/timeout",
        command=(sys.executable, "-c", "import time; time.sleep(2)"),
        inputs=(),
        outputs=(),
        policy=ExecutionPolicy(timeout_seconds=0.05),
    )
    cancelled_plan = ExecutionPlan(
        workflow="test/cancel",
        command=(sys.executable, "-c", "import time; time.sleep(2)"),
        inputs=(),
        outputs=(),
    )
    cancellation = threading.Event()
    cancellation.set()

    timed_out = FFmpegRunner().execute_plan(timeout_plan)
    cancelled = FFmpegRunner().execute_plan(cancelled_plan, cancellation=cancellation)

    assert timed_out.status is JobStatus.TIMED_OUT
    assert timed_out.exit_category == "timeout"
    assert cancelled.status is JobStatus.CANCELLED
    assert cancelled.exit_category == "cancelled"
