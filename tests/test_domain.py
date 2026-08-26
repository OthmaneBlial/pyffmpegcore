"""Contracts for typed plans, policies, results, and execution."""

from __future__ import annotations

import subprocess
import sys
import threading
from io import StringIO
from unittest.mock import MagicMock

import pytest

from pyffmpegcore import (
    CompressOptions,
    ExecutionPlan,
    ExecutionPolicy,
    ExecutionStep,
    FFmpegRunner,
    JobStatus,
    OverwritePolicy,
    TemporaryFilePolicy,
    ValidationError,
)
from pyffmpegcore.executor import _run_step


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


def test_execution_plan_runs_named_steps_in_order(tmp_path):
    output = tmp_path / "steps.txt"
    first = f"from pathlib import Path; Path({str(output)!r}).write_text('one')"
    second = f"from pathlib import Path; p=Path({str(output)!r}); p.write_text(p.read_text() + '-two')"
    plan = ExecutionPlan(
        workflow="test/steps",
        command=(sys.executable, "-c", first),
        inputs=(),
        outputs=(str(output),),
        steps=(
            ExecutionStep("first", (sys.executable, "-c", first)),
            ExecutionStep("second", (sys.executable, "-c", second)),
        ),
    )

    result = FFmpegRunner().execute_plan(plan)

    assert result.succeeded
    assert output.read_text(encoding="utf-8") == "one-two"


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


def test_execution_missing_binary_does_not_create_output_parent(tmp_path):
    output = tmp_path / "not-created" / "output.mp4"
    plan = ExecutionPlan(
        workflow="test/missing",
        command=(str(tmp_path / "missing-ffmpeg"), "-version"),
        inputs=(),
        outputs=(str(output),),
    )

    result = FFmpegRunner().execute_plan(plan)

    assert result.exit_category == "environment"
    assert result.returncode is None
    assert not output.parent.exists()


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


def test_execution_materializes_and_cleans_concat_manifest(tmp_path, monkeypatch):
    workspace = tmp_path / "temporary"

    def create_workspace(**_kwargs):
        workspace.mkdir()
        return str(workspace)

    monkeypatch.setattr("pyffmpegcore.executor.tempfile.mkdtemp", create_workspace)
    output = tmp_path / "manifest-copy.txt"
    code = "from pathlib import Path; import sys; Path(sys.argv[2]).write_text(Path(sys.argv[1]).read_text())"
    plan = ExecutionPlan(
        workflow="test/manifest",
        command=(sys.executable, "-c", code, "<pyffmpegcore-concat-manifest>", str(output)),
        inputs=(),
        outputs=(str(output),),
        metadata={"concat_manifest": [str(tmp_path / "clip's name.mp4")]},
    )

    result = FFmpegRunner().execute_plan(plan)

    assert result.succeeded
    assert "clip'\\''s name.mp4" in output.read_text(encoding="utf-8")
    assert not workspace.exists()


def test_execution_retains_temporary_workspace_on_error_when_requested(tmp_path, monkeypatch):
    workspace = tmp_path / "retained"

    def create_workspace(**_kwargs):
        workspace.mkdir()
        return str(workspace)

    monkeypatch.setattr("pyffmpegcore.executor.tempfile.mkdtemp", create_workspace)
    plan = ExecutionPlan(
        workflow="test/retained",
        command=(sys.executable, "-c", "raise SystemExit(7)", "<pyffmpegcore-passlog>"),
        inputs=(),
        outputs=(),
        policy=ExecutionPolicy(temporary_files=TemporaryFilePolicy.KEEP_ON_ERROR),
    )

    result = FFmpegRunner().execute_plan(plan)

    assert result.status is JobStatus.FAILED
    assert workspace.is_dir()
    assert any(str(workspace) in warning for warning in result.warnings)


def test_execution_emits_typed_structured_progress(tmp_path):
    output = tmp_path / "progress.txt"
    code = (
        "from pathlib import Path; import sys; "
        "print('frame=12'); print('out_time_us=1500000'); print('speed=1.25x'); print('progress=end'); "
        "Path(sys.argv[1]).write_text('done')"
    )
    plan = ExecutionPlan(
        workflow="test/progress",
        command=(sys.executable, "-c", code, str(output), "-progress", "pipe:1"),
        inputs=(),
        outputs=(str(output),),
    )
    events = []

    result = FFmpegRunner().execute_plan(plan, progress_callback=events.append)

    assert result.succeeded
    assert result.progress is not None
    assert result.progress.status == "end"
    assert result.progress.frame == 12
    assert result.progress.time_seconds == 1.5
    assert result.progress.speed == 1.25
    assert events == [result.progress]


def test_execution_replaces_invalid_utf8_without_stalling_pipe_drains(tmp_path):
    output = tmp_path / "unicode-output.txt"
    code = (
        "from pathlib import Path; import sys; "
        "sys.stderr.buffer.write(b'bad-byte: \\x9d\\n'); sys.stderr.flush(); "
        f"Path({str(output)!r}).write_text('done')"
    )
    plan = ExecutionPlan(
        workflow="test/unicode-stderr",
        command=(sys.executable, "-c", code),
        inputs=(),
        outputs=(str(output),),
    )

    result = FFmpegRunner().execute_plan(plan)

    assert result.succeeded
    assert result.stderr is not None
    assert "bad-byte: �" in result.stderr


def test_execution_falls_back_only_when_structured_progress_is_unsupported():
    code = (
        "import sys; "
        "has_progress = '-progress' in sys.argv; "
        "print(\"Unrecognized option 'progress'\" if has_progress else "
        "'frame= 12 fps=25.0 size= 1kB time=00:00:01.50 bitrate=10.0kbits/s speed=1.25x', file=sys.stderr); "
        "raise SystemExit(1 if has_progress else 0)"
    )
    plan = ExecutionPlan(
        workflow="test/progress-fallback",
        command=(sys.executable, "-c", code, "-progress", "pipe:1", "-nostats"),
        inputs=(),
        outputs=(),
    )
    events = []

    result = FFmpegRunner().execute_plan(plan, progress_callback=events.append)

    assert result.succeeded
    assert "-progress" not in result.command
    assert result.progress is not None and result.progress.status == "end"
    assert result.progress.time_seconds == 1.5
    assert [event.status for event in events] == ["running", "end"]
    assert any("legacy stderr fallback" in warning for warning in result.warnings)


def test_execution_removes_new_incomplete_output_after_runtime_failure(tmp_path):
    output = tmp_path / "partial.bin"
    code = "from pathlib import Path; import sys; Path(sys.argv[1]).write_bytes(b'partial'); raise SystemExit(7)"
    plan = ExecutionPlan(
        workflow="test/partial-output",
        command=(sys.executable, "-c", code, str(output)),
        inputs=(),
        outputs=(str(output),),
    )

    result = FFmpegRunner().execute_plan(plan)

    assert result.status is JobStatus.FAILED
    assert not output.exists()
    assert result.outputs[0]["exists"] is False
    assert any("Removed incomplete outputs" in warning for warning in result.warnings)


def test_keyboard_interrupt_terminates_child_as_cancelled(monkeypatch):
    process = MagicMock()
    process.stdout = StringIO("")
    process.stderr = StringIO("")
    process.poll.return_value = None
    process.returncode = -15
    popen_kwargs = {}

    def open_process(*_args, **kwargs):
        popen_kwargs.update(kwargs)
        return process

    monkeypatch.setattr("pyffmpegcore.executor.subprocess.Popen", open_process)

    def interrupt(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr("pyffmpegcore.executor.time.sleep", interrupt)
    outcome = _run_step(
        ["ffmpeg", "-version"],
        name="interrupt-test",
        deadline=None,
        cancellation=None,
        progress_callback=None,
    )

    assert outcome.status is JobStatus.CANCELLED
    assert outcome.category == "cancelled"
    assert popen_kwargs["stdin"] is subprocess.DEVNULL
    assert popen_kwargs["encoding"] == "utf-8"
    assert popen_kwargs["errors"] == "replace"
    assert "cancelled" in outcome.stderr
    process.terminate.assert_called_once()
