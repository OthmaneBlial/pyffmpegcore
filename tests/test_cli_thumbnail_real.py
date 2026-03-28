"""
Real-media tests for the CLI thumbnail command.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from pyffmpegcore.probe import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
@pytest.mark.parametrize(
    ("timestamp", "width", "height"),
    [
        ("00:00:00.100", 320, None),
        ("00:00:05.200", 200, 120),
    ],
)
def test_thumbnail_real_media(tmp_path, timestamp, width, height):
    """
    The thumbnail command should create readable images from the validated MP4 fixture.
    """
    media = ensure_downloaded_media()
    output_file = tmp_path / f"thumb-{width}-{height or 'auto'}.jpg"

    command = [
        sys.executable,
        "-m",
        "pyffmpegcore",
        "thumbnail",
        "--input",
        str(media["video_mp4_h264_1080p"]),
        "--output",
        str(output_file),
        "--timestamp",
        timestamp,
        "--width",
        str(width),
    ]
    if height is not None:
        command.extend(["--height", str(height)])

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert output_file.exists()
    metadata = FFprobeRunner().probe(str(output_file))
    assert metadata["video"]["codec"] == "mjpeg"
    assert metadata["video"]["width"] == width
    if height is not None:
        assert metadata["video"]["height"] == height
