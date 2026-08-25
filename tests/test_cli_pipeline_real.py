"""Real-media end-to-end pipeline preflight, execution, cache, and resume proof."""

from __future__ import annotations

import json

import pytest

from pyffmpegcore.cli import EXIT_OK, main
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_pipeline_cli_preflight_run_receipts_and_content_cache(tmp_path, capsys):
    fixtures = ensure_downloaded_media()
    pipeline_path = tmp_path / "video pipeline.json"
    state_path = tmp_path / "pipeline state.json"
    events_path = tmp_path / "pipeline events.jsonl"
    receipt_dir = tmp_path / "pipeline receipts"
    output_dir = tmp_path / "outputs ü"
    pipeline_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "name": "video_package",
                "variables": {
                    "SOURCE": str(fixtures["rich_streams_mkv"]),
                    "OUTPUT_DIR": str(output_dir),
                },
                "cache": {"enabled": True, "directory": ".cache", "content_aware": True},
                "steps": [
                    {
                        "id": "web",
                        "profile": "web/mp4-compatible",
                        "input": "${SOURCE}",
                        "output": "${OUTPUT_DIR}/video.mp4",
                    },
                    {
                        "id": "thumbnail",
                        "workflow": "thumbnail",
                        "input": "${steps.web.output}",
                        "output": "${OUTPUT_DIR}/poster.jpg",
                        "options": {"timestamp": "00:00:00.100", "width": 240},
                    },
                    {
                        "id": "audio",
                        "workflow": "extract-audio",
                        "input": "${steps.web.output}",
                        "output": "${OUTPUT_DIR}/audio.m4a",
                        "options": {"audio_bitrate": "96k"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    assert main(["pipeline", "run", str(pipeline_path), "--explain", "--plan-json"]) == EXIT_OK
    preview = json.loads(capsys.readouterr().out)
    assert preview["ok"] is True
    deferred = [
        check
        for step in preview["steps"]
        for check in step["preflight"]["checks"]
        if check["status"] == "warn" and "dependency" in check["message"]
    ]
    assert deferred

    arguments = [
        "pipeline",
        "run",
        str(pipeline_path),
        "--state",
        str(state_path),
        "--events",
        str(events_path),
        "--receipt-dir",
        str(receipt_dir),
        "--result-json",
    ]
    assert main(arguments) == EXIT_OK
    first = json.loads(capsys.readouterr().out)
    assert first["summary"] == {"total": 3, "succeeded": 3, "failed": 0, "blocked": 0, "cancelled": 0}
    assert {path.name for path in output_dir.iterdir()} == {"video.mp4", "poster.jpg", "audio.m4a"}
    assert len(list(receipt_dir.glob("*.receipt.json"))) == 3
    events = [json.loads(line) for line in events_path.read_text().splitlines()]
    assert {item["event"] for item in events} >= {"started", "succeeded"}

    assert main([*arguments, "--resume"]) == EXIT_OK
    second = json.loads(capsys.readouterr().out)
    assert [item["status"] for item in second["items"]] == ["cached", "cached", "cached"]
