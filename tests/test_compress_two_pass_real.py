"""
Real-media tests for two-pass FFmpegRunner.compress().
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyffmpegcore import FFmpegRunner, FFprobeRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_two_pass_compress_real_fixture_hits_target_tolerance(tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / "compressed_two_pass.mp4"
    target_size_kb = 700

    result = FFmpegRunner().compress(
        str(media["video_mp4_h264_1080p"]),
        str(output_file),
        target_size_kb=target_size_kb,
        overhead_pct=2.0,
        threads=1,
    )

    assert result.returncode == 0, result.stderr
    assert output_file.exists()

    actual_size_kb = output_file.stat().st_size / 1024
    assert abs(actual_size_kb - target_size_kb) <= target_size_kb * 0.15

    metadata = FFprobeRunner().probe(str(output_file))
    assert metadata["video"]["codec"] == "h264"
    assert metadata["audio"]["codec"] == "aac"

    pass_logs = list(tmp_path.glob("compressed_two_pass.mp4.pass*"))
    assert pass_logs == []


@pytest.mark.real_media
def test_two_pass_compress_rejects_too_small_target_real_fixture(tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / "too_small.mp4"

    with pytest.raises(ValueError) as exc_info:
        FFmpegRunner().compress(
            str(media["video_mp4_h264_1080p"]),
            str(output_file),
            target_size_kb=20,
        )

    assert "too small" in str(exc_info.value)
