"""Real-media contracts for stream and metadata permutations."""

from __future__ import annotations

import pytest

from pyffmpegcore import FFprobeRunner
from tests.media_utils import ensure_downloaded_media, load_manifest


def test_manifest_covers_every_required_media_permutation():
    fixture_ids = {fixture["id"] for fixture in load_manifest()["fixtures"]}

    assert {
        "video_mov_h264_640x360",
        "audio_wav_pcm",
        "rich_streams_mkv",
        "audio_cover_art_mp3",
        "rotated_video_mp4",
        "variable_frame_rate_mp4",
    } <= fixture_ids


@pytest.mark.real_media
def test_rich_fixture_preserves_multiple_audio_subtitles_chapters_and_unicode():
    media = FFprobeRunner().probe_media(str(ensure_downloaded_media()["rich_streams_mkv"]))

    assert media.tags["title"] == "Résumé – 東京"
    assert [stream.codec_type for stream in media.streams] == ["video", "audio", "audio", "subtitle"]
    assert [stream.language for stream in media.streams if stream.codec_type == "audio"] == ["eng", "fra"]
    assert next(stream for stream in media.streams if stream.codec_type == "subtitle").language == "fra"
    assert [chapter["title"] for chapter in media.chapters] == ["Début", "Fin"]


@pytest.mark.real_media
def test_cover_art_fixture_preserves_attached_picture_disposition():
    media = FFprobeRunner().probe_media(str(ensure_downloaded_media()["audio_cover_art_mp3"]))

    assert any(stream.codec_type == "audio" for stream in media.streams)
    cover = next(stream for stream in media.streams if stream.codec_type == "video")
    assert cover.codec_name == "mjpeg"
    assert cover.disposition["attached_pic"] == 1


@pytest.mark.real_media
def test_rotation_and_variable_frame_rate_remain_decision_visible():
    fixtures = ensure_downloaded_media()
    runner = FFprobeRunner()

    rotated = runner.probe_media(str(fixtures["rotated_video_mp4"]))
    variable = runner.probe_media(str(fixtures["variable_frame_rate_mp4"]))

    assert rotated.streams[0].rotation == 90.0
    assert variable.streams[0].details["r_frame_rate"] != variable.streams[0].details["avg_frame_rate"]
