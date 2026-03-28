"""
Real-media tests for the CLI speed command.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from pyffmpegcore.probe import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_speed_video_real_media(tmp_path):
    """
    The CLI should create a shorter playable video when speeding up the sample MP4.
    """
    media = ensure_downloaded_media()
    input_file = media["video_mp4_h264_1080p"]
    output_file = tmp_path / "faster.mp4"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "speed",
            "video",
            "--input",
            str(input_file),
            "--output",
            str(output_file),
            "--factor",
            "1.5",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert output_file.exists()
    input_duration = FFprobeRunner().probe(str(input_file))["duration"]
    output_duration = FFprobeRunner().probe(str(output_file))["duration"]
    assert output_duration < input_duration


@pytest.mark.real_media
def test_speed_audio_real_media(tmp_path):
    """
    The CLI should create a shorter playable audio file when speeding up the sample MP3.
    """
    media = ensure_downloaded_media()
    input_file = media["audio_mp3"]
    output_file = tmp_path / "faster.mp3"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "speed",
            "audio",
            "--input",
            str(input_file),
            "--output",
            str(output_file),
            "--factor",
            "1.25",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert output_file.exists()
    assert FFprobeRunner().probe(str(output_file))["audio"]["codec"] == "mp3"
    input_duration = FFprobeRunner().probe(str(input_file))["duration"]
    output_duration = FFprobeRunner().probe(str(output_file))["duration"]
    assert output_duration < input_duration
