"""
Real-media tests for FFprobeRunner using downloaded internet fixtures.
"""

from __future__ import annotations

import pytest

from pyffmpegcore import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_probe_real_mp4_fixture():
    media = ensure_downloaded_media()
    metadata = FFprobeRunner().probe(str(media["video_mp4_h264_1080p"]))

    assert metadata["format_name"].startswith("mov")
    assert metadata["duration"] > 5
    assert metadata["video"]["codec"] == "h264"
    assert metadata["video"]["width"] == 1920
    assert metadata["video"]["height"] == 1080
    assert metadata["audio"]["codec"] == "aac"


@pytest.mark.real_media
def test_probe_real_webm_fixture():
    media = ensure_downloaded_media()
    metadata = FFprobeRunner().probe(str(media["video_webm_vp9_1080p"]))

    assert "webm" in metadata["format_name"]
    assert metadata["duration"] > 5
    assert metadata["video"]["codec"] == "vp9"
    assert metadata["video"]["width"] == 1920
    assert metadata["video"]["height"] == 1080
    assert metadata["audio"]["codec"] == "opus"


@pytest.mark.real_media
def test_probe_real_mov_fixture_has_different_resolution():
    media = ensure_downloaded_media()
    metadata = FFprobeRunner().probe(str(media["video_mov_h264_640x360"]))

    assert "mov" in metadata["format_name"]
    assert metadata["video"]["codec"] == "h264"
    assert metadata["video"]["width"] == 640
    assert metadata["video"]["height"] == 360


@pytest.mark.real_media
@pytest.mark.parametrize(
    ("fixture_id", "codec", "sample_rate"),
    [
        ("audio_mp3", "mp3", 44100),
        ("audio_wav_pcm", "pcm_s16le", 44100),
    ],
)
def test_probe_real_audio_only_fixtures(fixture_id: str, codec: str, sample_rate: int):
    media = ensure_downloaded_media()
    runner = FFprobeRunner()

    metadata = runner.probe(str(media[fixture_id]))

    assert "video" not in metadata
    assert metadata["audio"]["codec"] == codec
    assert metadata["audio"]["sample_rate"] == sample_rate
    assert runner.get_resolution(str(media[fixture_id])) is None
    assert runner.get_duration(str(media[fixture_id])) > 3
