"""
Real-media coverage for the concatenate_videos example.
"""

from __future__ import annotations

import shutil

import pytest

from examples.concatenate_videos import (
    concatenate_videos_basic,
    concatenate_videos_reencode,
)
from pyffmpegcore import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


def _probe(path: str) -> dict:
    return FFprobeRunner().probe(path)


@pytest.mark.real_media
def test_concatenate_videos_basic_real_media_handles_special_paths(tmp_path):
    media = ensure_downloaded_media()
    first_clip = tmp_path / "clip one's source.mp4"
    second_clip = tmp_path / "clip two source.mp4"
    output_file = tmp_path / "joined output.mp4"

    shutil.copy2(media["video_mp4_h264_1080p"], first_clip)
    shutil.copy2(media["video_mp4_h264_1080p"], second_clip)

    first_metadata = _probe(str(first_clip))
    second_metadata = _probe(str(second_clip))

    result = concatenate_videos_basic(
        [str(first_clip), str(second_clip)],
        str(output_file),
    )

    assert result is True
    assert output_file.exists()

    output_metadata = _probe(str(output_file))
    assert output_metadata["video"]["codec"] == "h264"
    assert output_metadata["audio"]["codec"] == "aac"
    expected_duration = first_metadata["duration"] + second_metadata["duration"]
    assert output_metadata["duration"] == pytest.approx(expected_duration, abs=0.75)


@pytest.mark.real_media
def test_concatenate_videos_reencode_real_media_outputs_playable_mp4(tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / "joined_reencoded.mp4"

    first_input = str(media["video_mp4_h264_1080p"])
    second_input = str(media["video_webm_vp9_1080p"])
    first_metadata = _probe(first_input)
    second_metadata = _probe(second_input)

    result = concatenate_videos_reencode(
        [first_input, second_input],
        str(output_file),
    )

    assert result is True
    assert output_file.exists()

    output_metadata = _probe(str(output_file))
    assert output_metadata["format_name"] == "mov,mp4,m4a,3gp,3g2,mj2"
    assert output_metadata["video"]["codec"] == "h264"
    assert output_metadata["audio"]["codec"] == "aac"
    assert output_metadata["video"]["width"] == 1920
    assert output_metadata["video"]["height"] == 1080
    expected_duration = first_metadata["duration"] + second_metadata["duration"]
    assert output_metadata["duration"] == pytest.approx(expected_duration, abs=0.75)
