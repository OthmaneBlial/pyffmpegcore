"""
Real-media tests for the CLI probe command.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_probe_human_output_real_media():
    """
    The human-readable probe output should include the key summary fields.
    """
    media = ensure_downloaded_media()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "probe",
            "--input",
            str(media["video_mp4_h264_1080p"]),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "File:" in result.stdout
    assert "Format:" in result.stdout
    assert "Video stream:" in result.stdout
    assert "Audio stream:" in result.stdout


@pytest.mark.real_media
@pytest.mark.parametrize(
    ("fixture_id", "expected_codec_type"),
    [
        ("video_mp4_h264_1080p", "video"),
        ("video_webm_vp9_1080p", "video"),
        ("video_mov_h264_640x360", "video"),
        ("audio_mp3", "audio"),
        ("audio_wav_pcm", "audio"),
    ],
)
def test_probe_json_real_media(fixture_id, expected_codec_type):
    """
    JSON probe output should work across the core real fixture formats.
    """
    media = ensure_downloaded_media()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "probe",
            "--input",
            str(media[fixture_id]),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["filename"]
    assert payload["format_name"]
    if expected_codec_type == "video":
        assert payload["video"]["codec"]
    else:
        assert payload["audio"]["codec"]
