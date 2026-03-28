"""
Real-media tests for FFmpegRunner.extract_audio().
"""

from __future__ import annotations

import pytest

from pyffmpegcore import FFmpegRunner, FFprobeRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_extract_audio_real_mp4_to_mp3(tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / "extracted.mp3"

    result = FFmpegRunner().extract_audio(
        str(media["video_mp4_h264_1080p"]),
        str(output_file),
    )

    assert result.returncode == 0, result.stderr
    assert output_file.exists()

    metadata = FFprobeRunner().probe(str(output_file))
    assert "video" not in metadata
    assert metadata["audio"]["codec"] == "mp3"


@pytest.mark.real_media
def test_extract_audio_real_mp4_to_wav_with_resample(tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / "extracted.wav"

    result = FFmpegRunner().extract_audio(
        str(media["video_mp4_h264_1080p"]),
        str(output_file),
        sample_rate=22050,
        channels=1,
    )

    assert result.returncode == 0, result.stderr
    assert output_file.exists()

    metadata = FFprobeRunner().probe(str(output_file))
    assert "video" not in metadata
    assert metadata["audio"]["codec"] == "pcm_s16le"
    assert metadata["audio"]["sample_rate"] == 22050
    assert metadata["audio"]["channels"] == 1


@pytest.mark.real_media
def test_extract_audio_invalid_codec_fails_clearly(tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / "invalid.m4a"

    result = FFmpegRunner().extract_audio(
        str(media["video_mp4_h264_1080p"]),
        str(output_file),
        audio_codec="not_a_real_codec",
    )

    assert result.returncode != 0
    assert "Command:" in result.stderr
