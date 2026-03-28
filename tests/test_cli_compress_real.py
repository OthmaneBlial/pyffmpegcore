"""
Real-media tests for the CLI compress command.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from pyffmpegcore.probe import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_compress_single_pass_real_media(tmp_path):
    """
    The CLI compress command should reduce size for the validated single-pass case.
    """
    media = ensure_downloaded_media()
    input_file = media["video_mov_h264_640x360"]
    output_file = tmp_path / "compressed-single-pass.mp4"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "compress",
            "--input",
            str(input_file),
            "--output",
            str(output_file),
            "--crf",
            "32",
            "--preset",
            "fast",
            "--threads",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert output_file.exists()
    assert output_file.stat().st_size < input_file.stat().st_size

    metadata = FFprobeRunner().probe(str(output_file))
    assert metadata["video"]["codec"] == "h264"


@pytest.mark.real_media
def test_compress_two_pass_real_media(tmp_path):
    """
    The CLI compress command should support target-size two-pass compression.
    """
    media = ensure_downloaded_media()
    output_file = tmp_path / "compressed-two-pass.mp4"
    target_size_kb = 700

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "compress",
            "--input",
            str(media["video_mp4_h264_1080p"]),
            "--output",
            str(output_file),
            "--target-size-kb",
            str(target_size_kb),
            "--threads",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert output_file.exists()
    actual_size_kb = output_file.stat().st_size / 1024
    assert abs(actual_size_kb - target_size_kb) <= target_size_kb * 0.15
