"""Contracts for transparent orchestration and cache benchmark evidence."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_benchmark_cli_help_is_self_contained():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "benchmark_overhead.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "startup, processing, artifact, and pipeline-cache overhead" in result.stdout
    assert "--strict" in result.stdout


def test_published_baseline_is_versioned_and_passes_honest_contract():
    baseline = json.loads(
        (REPO_ROOT / "benchmarks" / "baseline-macos-arm64-2026-08-25.json").read_text(encoding="utf-8")
    )
    assert baseline["schema_version"] == "1.0"
    assert baseline["passed"] is True
    assert baseline["processing"]["raw_output_bytes"] == baseline["processing"]["pyffmpegcore_output_bytes"]
    assert baseline["cache"]["cold_status"] == "succeeded"
    assert baseline["cache"]["warm_status"] == "cached"
    assert baseline["cache"]["speedup"] > 1
    assert baseline["artifacts"]["wheel_bytes"] > 0
