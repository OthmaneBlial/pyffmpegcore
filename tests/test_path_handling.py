"""
Path-handling coverage for concat files and FFmpeg filter paths.
"""

from __future__ import annotations

import shutil

import pytest

from examples.concatenate_videos import concatenate_videos_basic
from examples.handle_subtitles import burn_subtitles
from pyffmpegcore import FFprobeRunner
from pyffmpegcore.runner import escape_path_for_concat, escape_path_for_filter
from tests.media_utils import ensure_downloaded_media


SHORT_SRT = """1
00:00:00,000 --> 00:00:02,500
Path handling subtitle line one.

2
00:00:03,000 --> 00:00:05,500
Path handling subtitle line two.
"""


def test_escape_path_for_concat_handles_spaces_and_quotes():
    path = "/tmp/dir with spaces/clip one's take.mp4"
    assert escape_path_for_concat(path) == "'/tmp/dir with spaces/clip one'\\''s take.mp4'"


def test_escape_path_for_filter_normalizes_windows_style_paths():
    path = r"C:\Media Files\clip's subtitle.srt"
    assert escape_path_for_filter(path) == r"C\:/Media Files/clip\'s subtitle.srt"


@pytest.mark.real_media
def test_real_media_workflows_handle_spaces_and_quotes_in_paths(tmp_path):
    media = ensure_downloaded_media()
    probe = FFprobeRunner()

    working_dir = tmp_path / "media dir with spaces" / "child's folder"
    working_dir.mkdir(parents=True)

    first_clip = working_dir / "clip one's source.mp4"
    second_clip = working_dir / "clip two source.mp4"
    concat_output = working_dir / "joined clip.mp4"
    subtitle_file = working_dir / "subtitle file's.srt"
    burned_output = working_dir / "burned clip.mp4"

    shutil.copy2(media["video_mp4_h264_1080p"], first_clip)
    shutil.copy2(media["video_mp4_h264_1080p"], second_clip)
    subtitle_file.write_text(SHORT_SRT, encoding="utf-8")

    assert concatenate_videos_basic(
        [str(first_clip), str(second_clip)],
        str(concat_output),
    ) is True
    assert burn_subtitles(
        str(first_clip),
        str(subtitle_file),
        str(burned_output),
    ) is True

    concat_metadata = probe.probe(str(concat_output))
    burned_metadata = probe.probe(str(burned_output))

    assert concat_metadata["video"]["codec"] == "h264"
    assert concat_metadata["audio"]["codec"] == "aac"
    assert burned_metadata["video"]["codec"] == "h264"
    assert burned_metadata["audio"]["codec"] == "aac"
