"""Real-media end-to-end pipeline preflight, execution, cache, and resume proof."""

from __future__ import annotations

import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from pyffmpegcore.cli import EXIT_OK, main
from pyffmpegcore.probe import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_direct_profile_and_pipeline_produce_equivalent_verified_media(tmp_path, capsys):
    """Input adapters sharing a plan must also deliver the same media contract."""
    source = ensure_downloaded_media()["video_mov_h264_640x360"]
    direct_output = tmp_path / "direct.mp4"
    pipeline_output = tmp_path / "pipeline.mp4"
    direct_receipt = tmp_path / "direct.receipt.json"
    pipeline_receipts = tmp_path / "pipeline-receipts"

    assert (
        main(
            [
                "profile",
                "run",
                "web/mp4-compatible",
                "--input",
                str(source),
                "--output",
                str(direct_output),
                "--receipt",
                str(direct_receipt),
                "--result-json",
            ]
        )
        == EXIT_OK
    )
    direct_result = json.loads(capsys.readouterr().out)

    pipeline_path = tmp_path / "equivalent.json"
    pipeline_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "name": "equivalent_profile",
                "steps": [
                    {
                        "id": "video",
                        "profile": "web/mp4-compatible",
                        "input": str(source),
                        "output": str(pipeline_output),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert (
        main(["pipeline", "run", str(pipeline_path), "--receipt-dir", str(pipeline_receipts), "--result-json"])
        == EXIT_OK
    )
    pipeline_result = json.loads(capsys.readouterr().out)

    assert direct_result["summary"]["succeeded"] == pipeline_result["summary"]["succeeded"] == 1
    assert len(list(pipeline_receipts.glob("*.receipt.json"))) == 1
    for receipt in (direct_receipt, *pipeline_receipts.glob("*.receipt.json")):
        assert main(["receipt", "validate", str(receipt), "--json"]) == EXIT_OK
        assert json.loads(capsys.readouterr().out)["valid"] is True

    direct_probe = FFprobeRunner().probe(str(direct_output))
    pipeline_probe = FFprobeRunner().probe(str(pipeline_output))
    for field in ("format_name", "duration", "video", "audio"):
        if field == "duration":
            assert abs(direct_probe[field] - pipeline_probe[field]) < 0.1
        elif field in {"video", "audio"}:
            for key in ("codec", "width", "height"):
                if key in direct_probe.get(field, {}) or key in pipeline_probe.get(field, {}):
                    assert direct_probe.get(field, {}).get(key) == pipeline_probe.get(field, {}).get(key)
        else:
            assert direct_probe[field] == pipeline_probe[field]


@pytest.mark.real_media
def test_pipeline_remote_secret_is_kept_out_of_result_and_receipt(tmp_path, monkeypatch, capsys):
    fixture = ensure_downloaded_media()["video_mp4_h264_1080p"]

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, _format, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(fixture.parent)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        secret = "integration-secret-do-not-log"
        source_url = f"http://user:{secret}@127.0.0.1:{server.server_port}/{fixture.name}?token={secret}"
        monkeypatch.setenv("SOURCE_URL", source_url)
        output = tmp_path / "web.mp4"
        receipts = tmp_path / "receipts"
        pipeline = tmp_path / "remote.json"
        pipeline.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "name": "remote_secret",
                    "secret_variables": ["SOURCE_URL"],
                    "steps": [
                        {
                            "id": "web",
                            "profile": "web/mp4-compatible",
                            "input": "${SOURCE_URL}",
                            "output": str(output),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        result_code = main(
            ["pipeline", "run", str(pipeline), "--var", "SOURCE_URL", "--receipt-dir", str(receipts), "--result-json"]
        )
        captured = capsys.readouterr()

        assert result_code == EXIT_OK, captured.err
        assert json.loads(captured.out)["summary"]["succeeded"] == 1
        assert output.is_file() and output.stat().st_size > 0
        receipt_files = list(receipts.glob("*.json"))
        assert len(receipt_files) == 1
        published = captured.out + captured.err + receipt_files[0].read_text(encoding="utf-8")
        assert secret not in published
        assert "<redacted>" in published
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


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
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    assert {item["event"] for item in events} >= {"started", "succeeded"}

    assert main([*arguments, "--resume"]) == EXIT_OK
    second = json.loads(capsys.readouterr().out)
    assert [item["status"] for item in second["items"]] == ["cached", "cached", "cached"]
