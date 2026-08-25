"""Installed-style real-media contracts for mixed, partial, resumable batches."""

from __future__ import annotations

import json

import pytest

from pyffmpegcore.cli import EXIT_PARTIAL_SUCCESS, main
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_cli_batch_partial_receipts_events_and_resume(tmp_path, capsys):
    fixtures = ensure_downloaded_media()
    manifest_path = tmp_path / "mixed batch.json"
    state_path = tmp_path / "batch state.json"
    events_path = tmp_path / "batch events.jsonl"
    receipts = tmp_path / "receipts"
    web_output = tmp_path / "web output.mp4"
    audio_output = tmp_path / "podcast ü.m4a"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "policy": {"max_workers": 2, "max_retries": 2, "max_input_bytes": "10MiB"},
                "jobs": [
                    {
                        "id": "web-video",
                        "profile": "web/mp4-compatible",
                        "input": str(fixtures["video_mov_h264_640x360"]),
                        "output": str(web_output),
                    },
                    {
                        "id": "podcast-audio",
                        "profile": "audio/podcast-speech",
                        "input": str(fixtures["audio_wav_pcm"]),
                        "output": str(audio_output),
                    },
                    {
                        "id": "missing-input",
                        "profile": "web/mp4-compatible",
                        "input": "does not exist.mp4",
                        "output": "never-created.mp4",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    arguments = [
        "batch",
        "run",
        str(manifest_path),
        "--state",
        str(state_path),
        "--events",
        str(events_path),
        "--receipt-dir",
        str(receipts),
        "--result-json",
    ]
    assert main(arguments) == EXIT_PARTIAL_SUCCESS
    first = json.loads(capsys.readouterr().out)

    assert first["summary"] == {"total": 3, "succeeded": 2, "failed": 1, "cancelled": 0, "resumed": 0}
    assert web_output.is_file()
    assert audio_output.is_file()
    assert {path.name for path in receipts.glob("*.json")} == {
        "web-video.receipt.json",
        "podcast-audio.receipt.json",
        "missing-input.receipt.json",
    }
    events = [json.loads(line) for line in events_path.read_text().splitlines()]
    assert [item["sequence"] for item in events] == list(range(1, len(events) + 1))
    assert {item["event"] for item in events} >= {"queued", "started", "succeeded", "failed"}

    assert main([*arguments, "--resume"]) == EXIT_PARTIAL_SUCCESS
    second = json.loads(capsys.readouterr().out)
    assert second["summary"] == {"total": 3, "succeeded": 2, "failed": 1, "cancelled": 0, "resumed": 2}
    assert [item["attempts"] for item in second["items"]] == [0, 0, 1]
