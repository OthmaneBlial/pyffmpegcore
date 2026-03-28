"""
Real-media tests for the CLI waveform command.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from pyffmpegcore.probe import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
@pytest.mark.parametrize(
    ("fixture_id", "width", "height", "colors"),
    [
        ("audio_mp3", 800, 200, "white"),
        ("video_mp4_h264_1080p", 640, 160, "red"),
    ],
)
def test_waveform_real_media(tmp_path, fixture_id, width, height, colors):
    """
    The CLI waveform command should create readable PNG outputs from verified sources.
    """
    media = ensure_downloaded_media()
    output_file = tmp_path / f"{fixture_id}-waveform.png"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "waveform",
            "--input",
            str(media[fixture_id]),
            "--output",
            str(output_file),
            "--width",
            str(width),
            "--height",
            str(height),
            "--colors",
            colors,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert output_file.exists()
    metadata = FFprobeRunner().probe(str(output_file))
    assert metadata["video"]["codec"] == "png"
    assert metadata["video"]["width"] == width
    assert metadata["video"]["height"] == height
