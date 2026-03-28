"""
Unit tests for CLI output helpers.
"""

from __future__ import annotations

from pyffmpegcore.cli import CLIContext, CLIProgressPrinter, format_bytes, report_batch_results


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
