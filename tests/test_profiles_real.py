"""Golden real-media contracts for every maintained built-in profile."""

from __future__ import annotations

import pytest

from pyffmpegcore import FFprobeRunner, ProfileRegistry, WorkflowEngine
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
@pytest.mark.parametrize(
    ("name", "input_id", "suffix", "expected_video", "expected_audio", "subtitle_language"),
    [
        ("web/mp4-compatible", "rich_streams_mkv", ".mp4", "h264", "aac", None),
        ("web/small-upload", "rich_streams_mkv", ".mp4", "h264", "aac", None),
        ("audio/podcast-speech", "audio_wav_pcm", ".m4a", None, "aac", None),
        ("subtitles/accessibility", "video_mov_h264_640x360", ".mp4", "h264", None, "fra"),
        ("archive/mezzanine", "rich_streams_mkv", ".mkv", "ffv1", "flac", None),
    ],
)
def test_builtin_profile_golden_media_contract(
    tmp_path,
    name,
    input_id,
    suffix,
    expected_video,
    expected_audio,
    subtitle_language,
):
    fixtures = ensure_downloaded_media()
    output = tmp_path / f"profile-output{suffix}"
    engine = WorkflowEngine()
    plan = ProfileRegistry().plan(
        name,
        engine.planner,
        str(fixtures[input_id]),
        str(output),
        subtitle_file=str(fixtures["subtitles_srt"]) if subtitle_language is not None else None,
        subtitle_language=subtitle_language,
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
    if subtitle_language is not None:
        assert codecs["subtitle"] == "mov_text"
        assert next(stream for stream in media.streams if stream.codec_type == "subtitle").language == subtitle_language
