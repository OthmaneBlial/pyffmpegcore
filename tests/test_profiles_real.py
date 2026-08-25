"""Golden real-media contracts for every maintained built-in profile."""

from __future__ import annotations

import pytest

from pyffmpegcore import FFprobeRunner, ProfileRegistry, WorkflowEngine
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
@pytest.mark.parametrize(
    ("name", "input_id", "suffix", "expected_video", "expected_audio", "needs_subtitle"),
    [
        ("web/mp4-compatible", "rich_streams_mkv", ".mp4", "h264", "aac", False),
        ("web/small-upload", "rich_streams_mkv", ".mp4", "h264", "aac", False),
        ("audio/podcast-speech", "audio_wav_pcm", ".m4a", None, "aac", False),
        ("subtitles/accessibility", "video_mov_h264_640x360", ".mp4", "h264", None, True),
        ("archive/mezzanine", "rich_streams_mkv", ".mkv", "ffv1", "flac", False),
    ],
)
def test_builtin_profile_golden_media_contract(
    tmp_path,
    name,
    input_id,
    suffix,
    expected_video,
    expected_audio,
    needs_subtitle,
):
    fixtures = ensure_downloaded_media()
    output = tmp_path / f"profile-output{suffix}"
    engine = WorkflowEngine()
    plan = ProfileRegistry().plan(
        name,
        engine.planner,
        str(fixtures[input_id]),
        str(output),
        subtitle_file=str(fixtures["subtitles_srt"]) if needs_subtitle else None,
    )

    batch = engine.run(plan)

    assert batch.succeeded, batch.items[0].result.stderr
    assert plan.metadata["profile"]["name"] == name
    media = FFprobeRunner().probe_media(str(output))
    codecs = {stream.codec_type: stream.codec_name for stream in media.streams}
    if expected_video:
        assert codecs["video"] == expected_video
    if expected_audio:
        assert codecs["audio"] == expected_audio
    if needs_subtitle:
        assert codecs["subtitle"] == "mov_text"
