"""End-to-end CLI contracts for private run receipts and bug reports."""

from __future__ import annotations

import json

import pytest

from pyffmpegcore.cli import main
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_cli_writes_valid_redacted_receipt_and_reports_it_in_json(tmp_path, capsys):
    source = ensure_downloaded_media()["video_mp4_h264_1080p"]
    output = tmp_path / "private-output" / "thumb.jpg"
    receipt_path = tmp_path / "private-receipts" / "run.json"

    returncode = main(
        [
            "thumbnail",
            "--input",
            str(source),
            "--output",
            str(output),
            "--receipt",
            str(receipt_path),
            "--hash-content",
            "--result-json",
        ]
    )
    result_payload = json.loads(capsys.readouterr().out)
    rendered_receipt = receipt_path.read_text(encoding="utf-8")
    receipt = json.loads(rendered_receipt)

    assert returncode == 0
    assert result_payload["receipt"] == {"schema_version": "1.0", "path": str(receipt_path)}
    assert receipt["summary"] == {"total": 1, "succeeded": 1, "failed": 0}
    assert receipt["items"][0]["output_probe"]["streams"][0]["codec"] == "mjpeg"
    assert {item["algorithm"] for item in receipt["content_hashes"]} == {"sha256"}
    assert str(source.parent) not in rendered_receipt
    assert str(output.parent) not in rendered_receipt

    assert main(["receipt", "validate", str(receipt_path), "--json"]) == 0
    validation = json.loads(capsys.readouterr().out)
    assert validation == {
        "schema_version": "1.0",
        "valid": True,
        "receipt_schema_version": "1.0",
        "items": 1,
    }

    migrated_path = tmp_path / "migrated.json"
    assert main(["receipt", "migrate", str(receipt_path), "--output", str(migrated_path)]) == 0
    capsys.readouterr()
    assert json.loads(migrated_path.read_text(encoding="utf-8"))["schema_version"] == "1.0"


@pytest.mark.real_media
def test_cli_bug_report_combines_doctor_and_receipt_without_media_access(tmp_path, capsys, monkeypatch):
    source = ensure_downloaded_media()["video_mov_h264_640x360"]
    receipt_path = tmp_path / "receipt.json"
    assert (
        main(
            [
                "thumbnail",
                "--input",
                str(source),
                "--output",
                str(tmp_path / "thumb.jpg"),
                "--receipt",
                str(receipt_path),
                "--quiet",
            ]
        )
        == 0
    )
    capsys.readouterr()
    monkeypatch.setattr(
        "pyffmpegcore.receipt.FFprobeRunner.probe_media",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("bug report must not probe media")),
    )

    report_path = tmp_path / "bug-report.json"
    assert main(["receipt", "bug-report", str(receipt_path), "--output", str(report_path)]) == 0
    capsys.readouterr()
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["schema_version"] == "1.0"
    assert report["receipt"]["schema_version"] == "1.0"
    assert "ffmpeg" in report["doctor"]
    assert str(source.parent) not in report_path.read_text(encoding="utf-8")


def test_cli_rejects_invalid_receipt_and_hashing_without_receipt(tmp_path, capsys):
    broken = tmp_path / "broken.json"
    broken.write_text('{"schema_version":"99"}', encoding="utf-8")

    assert main(["receipt", "validate", str(broken)]) == 4
    assert "invalid receipt" in capsys.readouterr().err
    assert main(["convert", "--input", "in", "--output", "out", "--hash-content"]) == 2
    assert "requires --receipt" in capsys.readouterr().err
