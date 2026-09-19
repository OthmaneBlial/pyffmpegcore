"""The CI compatibility summary must fail closed on incomplete evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.summarize_compatibility import render_report


def write_cell(root: Path, system: str, python: str, *, wheel: str = "same", returncode: int = 0) -> Path:
    directory = root / f"compatibility-{system}-py{python}"
    directory.mkdir()
    doctor = {
        "platform": {"system": "Darwin" if system == "macOS" else system, "machine": "arm64"},
        "python": {"version": f"{python}.1"},
        "ffmpeg": {"version": "ffmpeg version 9.0.1 Copyright (c) FFmpeg developers"},
    }
    report = {
        "commands": [
            {"name": "cli-doctor", "returncode": returncode, "stdout": json.dumps(doctor)},
        ],
        "artifact": {"sha256": wheel},
    }
    catalog = {
        "catalog_valid": True,
        "catalog_errors": [],
        "workflows": {"images/webp": {"missing": ["encoder:libwebp"] if system == "macOS" else []}},
    }
    (directory / "compatibility-report.json").write_text(json.dumps(report), encoding="utf-8")
    (directory / "capability-catalog-report.json").write_text(json.dumps(catalog), encoding="utf-8")
    return directory


def make_six_cells(root: Path) -> None:
    for system in ("Linux", "macOS", "Windows"):
        for python in ("3.10", "3.14"):
            write_cell(root, system, python)


def test_summary_distinguishes_tested_cells_and_missing_capability(tmp_path: Path) -> None:
    make_six_cells(tmp_path)
    report = render_report(tmp_path, "https://example.test/actions/runs/1")
    assert report.count("1/1") == 6
    assert "macOS | arm64 | 3.14.1" in report
    assert "images/webp: encoder:libwebp" in report
    assert "Wheel SHA-256: `same`" in report


def test_summary_refuses_missing_cell_or_mixed_wheel(tmp_path: Path) -> None:
    make_six_cells(tmp_path)
    missing = tmp_path / "compatibility-Windows-py3.14"
    for file in missing.iterdir():
        file.unlink()
    missing.rmdir()
    with pytest.raises(ValueError, match="Expected six"):
        render_report(tmp_path, "https://example.test/actions/runs/1")
    write_cell(tmp_path, "Windows", "3.14", wheel="different")
    with pytest.raises(ValueError, match="same wheel"):
        render_report(tmp_path, "https://example.test/actions/runs/1")


def test_summary_refuses_failed_check(tmp_path: Path) -> None:
    make_six_cells(tmp_path)
    directory = tmp_path / "compatibility-Linux-py3.10"
    report_path = directory / "compatibility-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["commands"][0]["returncode"] = 1
    report_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="failed checks"):
        render_report(tmp_path, "https://example.test/actions/runs/1")


def test_summary_counts_only_validated_expected_refusals(tmp_path: Path) -> None:
    make_six_cells(tmp_path)
    report_path = tmp_path / "compatibility-Linux-py3.10" / "compatibility-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["commands"].append(
        {"name": "missing-encoder-remedy", "returncode": 4, "expected_returncode": 4, "passed": True}
    )
    report_path.write_text(json.dumps(report), encoding="utf-8")
    assert "Linux | arm64 | 3.10.1 | ffmpeg version 9.0.1 | 2/2" in render_report(
        tmp_path, "https://example.test/actions/runs/1"
    )

    report["commands"][-1]["passed"] = False
    report_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="missing-encoder-remedy"):
        render_report(tmp_path, "https://example.test/actions/runs/1")
