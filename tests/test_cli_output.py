"""
Unit tests for CLI output helpers.
"""

from __future__ import annotations

import pytest

from pyffmpegcore import ExecutionPlan, JobResult, JobStatus, PreflightReport, PreparedWorkflow, WorkflowExecution
from pyffmpegcore.cli import (
    CLIContext,
    CLIProgressPrinter,
    _render_execution_successes,
    format_bytes,
    report_batch_results,
)
from pyffmpegcore.workflow import WorkflowBatch


def test_format_bytes_formats_common_sizes():
    """
    Byte formatting should stay compact and readable.
    """
    assert format_bytes(512) == "512 B"
    assert format_bytes(2048) == "2.0 KB"
    assert format_bytes(5 * 1024 * 1024) == "5.0 MB"


def test_progress_printer_finishes_cleanly(capsys):
    """
    Progress output should end with a readable completion line.
    """
    printer = CLIProgressPrinter(total_duration=10.0)
    printer({"time_seconds": 5.0, "status": "progress"})
    printer({"status": "end"})

    captured = capsys.readouterr()
    assert "Progress:" in captured.err
    assert "100% complete" in captured.err


def test_progress_printer_clears_longer_previous_status(capsys):
    """A carriage-return update must not leave stale characters on screen."""
    printer = CLIProgressPrinter(total_duration=123456.78)
    printer({"time_seconds": 123456.78, "status": "progress"})
    printer({"status": "end"})

    terminal_line = capsys.readouterr().err.split("\r")[-1].rstrip("\n")
    assert terminal_line.rstrip() == "Progress: 100% complete"
    assert len(terminal_line) > len("Progress: 100% complete")


def test_report_batch_results_prints_summary(capsys):
    """
    Batch commands should print a concise success/failure summary.
    """
    report_batch_results(
        CLIContext(),
        "Image conversion",
        {"successful": 2, "failed": 1, "total": 3},
    )

    captured = capsys.readouterr()
    assert "Image conversion: 2 succeeded, 1 failed, 3 total" in captured.out


@pytest.mark.parametrize(
    ("workflow", "message"),
    [
        ("convert", "FFprobe unavailable; output media was not verified."),
        ("images/convert", "FFprobe unavailable for 1 image output(s); media verification was skipped."),
    ],
)
def test_success_summary_discloses_unavailable_output_verification(tmp_path, capsys, monkeypatch, workflow, message):
    output = tmp_path / "result.mp4"
    plan = ExecutionPlan(workflow, ("ffmpeg",), (), (str(output),))
    result = JobResult(
        workflow=workflow,
        command=("ffmpeg",),
        status=JobStatus.SUCCEEDED,
        exit_category="ok",
        returncode=0,
        elapsed_seconds=0,
        outputs=(
            {
                "path": str(output),
                "exists": True,
                "size_bytes": 1,
                "verification": {"status": "unavailable", "reason": "missing ffprobe"},
            },
        ),
    )
    report = PreflightReport(workflow, ())
    item = WorkflowExecution(None, str(output), report, result)
    bundle = WorkflowBatch(PreparedWorkflow(plan, report), (item,))
    monkeypatch.setattr("pyffmpegcore.cli.summarize_output_file", lambda *_args: None)

    _render_execution_successes(CLIContext(), bundle)

    assert message in capsys.readouterr().out
