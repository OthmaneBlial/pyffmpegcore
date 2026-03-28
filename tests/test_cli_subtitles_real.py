"""
Real-media tests for the CLI subtitles command group.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys

import pytest

from pyffmpegcore import FFmpegRunner
from tests.media_utils import ensure_downloaded_media


SHORT_SRT = """1
00:00:00,000 --> 00:00:02,500
Welcome to the CLI subtitle file!

2
00:00:03,000 --> 00:00:05,500
This subtitle line is used for CLI validation.
"""


def _probe_streams(path: str) -> list[dict]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=index,codec_type,codec_name:stream_tags=language,title",
            "-of",
            "json",
            path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["streams"]


@pytest.mark.real_media
def test_subtitles_add_and_extract_real_media(tmp_path):
    """
    The CLI should add a subtitle track and extract it back out as SRT.
    """
    media = ensure_downloaded_media()
    subtitle_file = tmp_path / "external subtitles.srt"
    subtitle_file.write_text(SHORT_SRT, encoding="utf-8")
    muxed_output = tmp_path / "video-with-subtitles.mp4"
    extracted_output = tmp_path / "extracted.srt"

    added = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "subtitles",
            "add",
            "--video",
            str(media["video_mp4_h264_1080p"]),
            "--subtitle",
            str(subtitle_file),
            "--output",
            str(muxed_output),
            "--language",
            "eng",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert added.returncode == 0
    streams = _probe_streams(str(muxed_output))
    subtitle_streams = [stream for stream in streams if stream["codec_type"] == "subtitle"]
    assert len(subtitle_streams) == 1
    assert subtitle_streams[0]["codec_name"] == "mov_text"
    assert subtitle_streams[0].get("tags", {}).get("language") == "eng"

    extracted = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "subtitles",
            "extract",
            "--video",
            str(muxed_output),
            "--output",
            str(extracted_output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert extracted.returncode == 0
    extracted_text = extracted_output.read_text(encoding="utf-8")
    assert "Welcome to the CLI subtitle file!" in extracted_text
    assert "CLI validation" in extracted_text


@pytest.mark.real_media
def test_subtitles_burn_real_media_changes_frame_content(tmp_path):
    """
    Burning subtitles should change the rendered frame content.
    """
    media = ensure_downloaded_media()
    subtitle_file = tmp_path / "subtitles with one's cues.srt"
    subtitle_file.write_text(SHORT_SRT, encoding="utf-8")
    burned_output = tmp_path / "video-burned-subtitles.mp4"
    original_frame = tmp_path / "original-frame.jpg"
    burned_frame = tmp_path / "burned-frame.jpg"

    burned = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "subtitles",
            "burn",
            "--video",
            str(media["video_mp4_h264_1080p"]),
            "--subtitle",
            str(subtitle_file),
            "--output",
            str(burned_output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert burned.returncode == 0
    streams = _probe_streams(str(burned_output))
    assert [stream["codec_type"] for stream in streams] == ["video", "audio"]

    runner = FFmpegRunner()
    assert runner.extract_thumbnail(
        str(media["video_mp4_h264_1080p"]),
        str(original_frame),
        timestamp="00:00:01.000",
        width=960,
    ).returncode == 0
    assert runner.extract_thumbnail(
        str(burned_output),
        str(burned_frame),
        timestamp="00:00:01.000",
        width=960,
    ).returncode == 0

    assert hashlib.sha256(original_frame.read_bytes()).hexdigest() != hashlib.sha256(
        burned_frame.read_bytes()
    ).hexdigest()
