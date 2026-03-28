"""
Real-media tests for the CLI extract-audio command.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from pyffmpegcore.probe import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
@pytest.mark.parametrize(
    "output_name",
    ["audio.mp3", "audio.wav"],
)
def test_extract_audio_real_media(tmp_path, output_name):
    """
    The CLI should extract playable audio-only outputs from the sample MP4 fixture.
    """
    media = ensure_downloaded_media()
    output_file = tmp_path / output_name

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "extract-audio",
            "--input",
            str(media["video_mp4_h264_1080p"]),
            "--output",
            str(output_file),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert output_file.exists()
    metadata = FFprobeRunner().probe(str(output_file))
    assert metadata["audio"]["codec"]
    assert "video" not in metadata
