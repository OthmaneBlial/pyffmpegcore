"""
Real-media tests for FFmpegRunner.extract_thumbnail().
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
    ("timestamp", "width", "height"),
    [
        ("00:00:00.100", 320, None),
        ("00:00:05.200", 200, 120),
    ],
)
def test_extract_thumbnail_real_fixture(timestamp: str, width: int, height: int | None, tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / f"thumb_{timestamp.replace(':', '_')}.jpg"

    result = FFmpegRunner().extract_thumbnail(
        str(media["video_mp4_h264_1080p"]),
        str(output_file),
        timestamp=timestamp,
        width=width,
        height=height,
    )

    assert result.returncode == 0, result.stderr
    assert output_file.exists()

    image_stream = _probe_image(str(output_file))
    assert image_stream["codec_name"] in {"mjpeg", "jpeg"}
    assert image_stream["width"] == width
    if height is not None:
        assert image_stream["height"] == height


@pytest.mark.real_media
def test_extract_thumbnail_invalid_timestamp_fails_clearly(tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / "invalid.jpg"

    result = FFmpegRunner().extract_thumbnail(
        str(media["video_mp4_h264_1080p"]),
        str(output_file),
        timestamp="not-a-time",
    )

    assert result.returncode != 0
    assert "Command:" in result.stderr
