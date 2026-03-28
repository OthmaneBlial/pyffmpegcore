"""
Real-media tests for the CLI convert command.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from pyffmpegcore.probe import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
@pytest.mark.parametrize(
    ("fixture_id", "expects_audio"),
    [
        ("video_webm_vp9_1080p", True),
        ("video_mov_h264_640x360", False),
    ],
)
def test_convert_real_media_to_mp4(tmp_path, fixture_id, expects_audio):
    """
    The CLI convert command should produce a readable MP4 from the verified source formats.
    """
    media = ensure_downloaded_media()
    output_file = tmp_path / f"{fixture_id}.mp4"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "convert",
            "--input",
            str(media[fixture_id]),
            "--output",
            str(output_file),
            "--video-codec",
            "libx264",
            "--audio-codec",
            "aac",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert output_file.exists()
    metadata = FFprobeRunner().probe(str(output_file))
    assert metadata["format_name"].startswith("mov,mp4")
    assert metadata["video"]["codec"] == "h264"
    if expects_audio:
        assert metadata["audio"]["codec"] == "aac"
    else:
        assert "audio" not in metadata
