"""
Real-media tests for the CLI concat command.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

import pytest

from pyffmpegcore.probe import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_concat_copy_real_media_handles_special_paths(tmp_path):
    """
    Copy-mode concat should handle clips whose paths contain spaces and apostrophes.
    """
    media = ensure_downloaded_media()
    first_clip = tmp_path / "clip one's source.mp4"
    second_clip = tmp_path / "clip two source.mp4"
    shutil.copy2(media["video_mp4_h264_1080p"], first_clip)
    shutil.copy2(media["video_mp4_h264_1080p"], second_clip)
    output_file = tmp_path / "joined clip.mp4"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "concat",
            "--mode",
            "copy",
            "--inputs",
            str(first_clip),
            str(second_clip),
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
    assert metadata["video"]["codec"] == "h264"
    assert metadata["duration"] == pytest.approx(11.5, abs=0.5)


@pytest.mark.real_media
def test_concat_reencode_real_media_mixed_formats(tmp_path):
    """
    Re-encode concat should join mixed MP4 and WebM inputs into a readable MP4 output.
    """
    media = ensure_downloaded_media()
    output_file = tmp_path / "joined-reencoded.mp4"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "concat",
            "--mode",
            "reencode",
            "--inputs",
            str(media["video_mp4_h264_1080p"]),
            str(media["video_webm_vp9_1080p"]),
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
    assert metadata["video"]["codec"] == "h264"
    assert metadata["audio"]["codec"] == "aac"
