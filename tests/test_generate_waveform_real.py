"""
Real-media tests for FFmpegRunner.generate_waveform().
"""

from __future__ import annotations

import json
import subprocess

import pytest

from pyffmpegcore import FFmpegRunner
from tests.media_utils import ensure_downloaded_media


def _probe_image(path: str) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,width,height",
            "-of",
            "json",
            path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["streams"][0]


@pytest.mark.real_media
@pytest.mark.parametrize(
    ("fixture_id", "width", "height", "colors"),
    [
        ("audio_mp3", 800, 200, "white"),
        ("video_mp4_h264_1080p", 640, 160, "red"),
    ],
)
def test_generate_waveform_real_media(fixture_id: str, width: int, height: int, colors: str, tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / f"waveform_{fixture_id}.png"

    result = FFmpegRunner().generate_waveform(
        str(media[fixture_id]),
        str(output_file),
        width=width,
        height=height,
        colors=colors,
    )

    assert result.returncode == 0, result.stderr
    assert output_file.exists()

    image_stream = _probe_image(str(output_file))
    assert image_stream["codec_name"] == "png"
    assert image_stream["width"] == width
    assert image_stream["height"] == height


@pytest.mark.real_media
def test_generate_waveform_without_audio_fails_clearly(tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / "waveform.png"

    result = FFmpegRunner().generate_waveform(
        str(media["video_mov_h264_640x360"]),
        str(output_file),
    )

    assert result.returncode != 0
    assert "Command:" in result.stderr
