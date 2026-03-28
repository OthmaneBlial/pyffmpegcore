"""
Real-media tests for FFmpegRunner.resize().
"""

from __future__ import annotations

import json
import subprocess

import pytest

from pyffmpegcore import FFmpegRunner, FFprobeRunner
from tests.media_utils import ensure_downloaded_media


def _probe_video_stream(path: str) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height,pix_fmt",
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
    ("width", "height"),
    [
        (320, 180),
        (180, 320),
    ],
)
def test_resize_real_mov_fixture(width: int, height: int, tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / f"resized_{width}x{height}.mp4"

    result = FFmpegRunner().resize(
        str(media["video_mov_h264_640x360"]),
        str(output_file),
        width,
        height,
        video_codec="libx264",
        audio_codec="aac",
        threads=1,
    )

    assert result.returncode == 0, result.stderr
    assert output_file.exists()

    metadata = FFprobeRunner().probe(str(output_file))
    assert metadata["video"]["width"] == width
    assert metadata["video"]["height"] == height
    assert metadata["video"]["codec"] == "h264"

    video_stream = _probe_video_stream(str(output_file))
    assert video_stream["pix_fmt"] == "yuv420p"
