"""
Real-media tests for FFmpegRunner.adjust_speed().
"""

from __future__ import annotations

import pytest

from pyffmpegcore import FFmpegRunner, FFprobeRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
@pytest.mark.parametrize(
    ("speed_factor", "relation"),
    [
        (3.0, "faster"),
        (0.5, "slower"),
    ],
)
def test_adjust_speed_real_fixture(speed_factor: float, relation: str, tmp_path):
    media = ensure_downloaded_media()
    input_file = media["video_mp4_h264_1080p"]
    output_file = tmp_path / f"speed_{speed_factor}.mp4"

    input_metadata = FFprobeRunner().probe(str(input_file))
    result = FFmpegRunner().adjust_speed(
        str(input_file),
        str(output_file),
        speed_factor=speed_factor,
        audio_pitch=True,
    )

    assert result.returncode == 0, result.stderr
    assert output_file.exists()

    output_metadata = FFprobeRunner().probe(str(output_file))
    assert output_metadata["video"]["codec"] == "h264"
    assert output_metadata["audio"]["codec"] == "aac"

    input_duration = input_metadata["duration"]
    output_duration = output_metadata["duration"]

    if relation == "faster":
        assert output_duration < input_duration / 2
    else:
        assert output_duration > input_duration * 1.8
