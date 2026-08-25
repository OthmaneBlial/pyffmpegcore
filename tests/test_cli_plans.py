"""Every writing command must expose a non-mutating JSON plan."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from pyffmpegcore.capabilities import CapabilityInventory
from pyffmpegcore.cli import main

MEDIA_ROOT = Path(__file__).parent / "media" / "downloads"
VIDEO = MEDIA_ROOT / "sample_mp4_h264.mp4"
AUDIO = MEDIA_ROOT / "sample_audio_mp3.mp3"
SUBTITLE = MEDIA_ROOT / "sample_subtitles.srt"


@pytest.fixture(scope="module")
def capability_inventory():
    return CapabilityInventory.inspect("ffmpeg")


@pytest.mark.parametrize(
    "arguments",
    [
        ["convert", "--input", str(VIDEO), "--output", "{tmp}/convert.mp4", "--video-codec", "libx264"],
        ["compress", "--input", str(VIDEO), "--output", "{tmp}/compress.mp4", "--crf", "28"],
        [
            "compress",
            "--input",
            str(VIDEO),
            "--output",
            "{tmp}/compress-sized.mp4",
            "--target-size",
            "5MB",
            "--min-video-bitrate",
            "100k",
        ],
        ["extract-audio", "--input", str(VIDEO), "--output", "{tmp}/audio.mp3"],
        ["thumbnail", "--input", str(VIDEO), "--output", "{tmp}/thumb.jpg"],
        ["waveform", "--input", str(AUDIO), "--output", "{tmp}/wave.png"],
        ["speed", "video", "--input", str(VIDEO), "--output", "{tmp}/fast.mp4", "--factor", "1.5"],
        ["speed", "audio", "--input", str(AUDIO), "--output", "{tmp}/fast.mp3", "--factor", "1.25"],
        ["concat", "--inputs", str(VIDEO), str(VIDEO), "--output", "{tmp}/concat.mp4"],
        [
            "concat",
            "--inputs",
            str(VIDEO),
            str(VIDEO),
            "--output",
            "{tmp}/concat-reencode.mp4",
            "--mode",
            "reencode",
        ],
        [
            "subtitles",
            "add",
            "--video",
            str(VIDEO),
            "--subtitle",
            str(SUBTITLE),
            "--output",
            "{tmp}/subtitled.mp4",
        ],
        ["subtitles", "extract", "--video", str(VIDEO), "--output", "{tmp}/captions.srt"],
        [
            "subtitles",
            "burn",
            "--video",
            str(VIDEO),
            "--subtitle",
            str(SUBTITLE),
            "--output",
            "{tmp}/burned.mp4",
        ],
        ["mix-audio", "mix", "--inputs", str(AUDIO), str(AUDIO), "--output", "{tmp}/mix.mp3"],
        ["mix-audio", "concat", "--inputs", str(AUDIO), str(AUDIO), "--output", "{tmp}/joined.mp3"],
        ["mix-audio", "mashup", "--inputs", str(AUDIO), str(AUDIO), "--output", "{tmp}/mashup.mp3"],
        [
            "mix-audio",
            "background",
            "--main-input",
            str(AUDIO),
            "--background-input",
            str(AUDIO),
            "--output",
            "{tmp}/background.mp3",
        ],
        ["normalize-audio", "--input", str(AUDIO), "--output", "{tmp}/normalized.mp3"],
        ["images", "convert", "--input-dir", str(MEDIA_ROOT), "--output-dir", "{tmp}/images"],
        ["images", "optimize", "--input-dir", str(MEDIA_ROOT), "--output-dir", "{tmp}/optimized"],
        ["images", "webp", "--input-dir", str(MEDIA_ROOT), "--output-dir", "{tmp}/webp"],
    ],
)
def test_every_writing_command_has_a_non_mutating_json_plan(
    arguments,
    tmp_path,
    capsys,
    monkeypatch,
    capability_inventory,
):
    monkeypatch.setattr(
        "pyffmpegcore.preflight.CapabilityInventory.inspect",
        lambda _binary: capability_inventory,
    )
    rendered = [value.format(tmp=str(tmp_path)) for value in arguments]

    returncode = main([*rendered, "--dry-run", "--plan-json"])
    captured = capsys.readouterr()

    assert returncode in {0, 4}, captured.err
    payload = json.loads(captured.out)
    assert payload["schema_version"] == "1.0"
    assert isinstance(payload["plan"]["command"], list)
    assert payload["plan"]["outputs"]
    for output in payload["plan"]["outputs"]:
        assert not Path(output).exists()


def test_preview_never_executes_shell_metacharacters(tmp_path, capsys, monkeypatch, capability_inventory):
    source = tmp_path / "$(touch SHOULD_NOT_EXIST).mp4"
    shutil.copyfile(VIDEO, source)
    output = tmp_path / "output; touch ALSO_NOT_CREATED.mp4"
    monkeypatch.setattr("pyffmpegcore.preflight.CapabilityInventory.inspect", lambda _binary: capability_inventory)

    returncode = main(
        [
            "convert",
            "--input",
            str(source),
            "--output",
            str(output),
            "--video-codec",
            "libx264",
            "--explain",
        ]
    )
    captured = capsys.readouterr()

    assert returncode == 0, captured.err
    assert "Argument vectors (display only; no shell is used)" in captured.out
    assert not output.exists()
    assert not (tmp_path / "SHOULD_NOT_EXIST").exists()
    assert not (tmp_path / "ALSO_NOT_CREATED.mp4").exists()


def test_preview_reports_invalid_bitrate_without_a_traceback(tmp_path, capsys):
    returncode = main(
        [
            "compress",
            "--input",
            str(VIDEO),
            "--output",
            str(tmp_path / "output.mp4"),
            "--target-size",
            "5MB",
            "--min-video-bitrate",
            "fast",
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()

    assert returncode == 4
    assert "bitrate must be" in captured.err
    assert "Traceback" not in captured.err
