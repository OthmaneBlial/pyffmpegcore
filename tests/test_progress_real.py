"""
Real-media tests for FFmpeg progress callbacks.
"""

from __future__ import annotations

import pytest

from pyffmpegcore import FFmpegRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_progress_callback_emits_real_updates(tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / "progress_output.mp4"
    updates = []

    result = FFmpegRunner().compress(
        str(media["video_mov_h264_640x360"]),
        str(output_file),
        crf=28,
        preset="medium",
        threads=1,
        progress_callback=updates.append,
    )

    assert result.returncode == 0, result.stderr
    assert output_file.exists()
    assert updates

    progress_updates = [update for update in updates if update.status == "running"]
    end_updates = [update for update in updates if update.status == "end"]

    assert progress_updates
    assert end_updates

    time_points = [update.time_seconds for update in updates if update.time_seconds is not None]
    assert time_points
    assert time_points == sorted(time_points)

    frame_points = [update.frame for update in updates if update.frame is not None]
    assert frame_points == sorted(frame_points)

    speed_points = [update.speed for update in updates if update.speed is not None]
    assert any(speed > 0 for speed in speed_points)
