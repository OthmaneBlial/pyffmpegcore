"""
Real-media tests for FFmpegRunner.convert().
"""

from __future__ import annotations

import pytest

from pyffmpegcore import FFmpegRunner, FFprobeRunner
from tests.media_utils import ensure_downloaded_media
from tests.mp4_utils import top_level_mp4_atoms


@pytest.mark.real_media
def test_convert_mov_to_mp4_real_fixture(tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / "converted_from_mov.mp4"

    result = FFmpegRunner().convert(
        str(media["video_mov_h264_640x360"]),
        str(output_file),
        video_codec="libx264",
        audio_codec="aac",
        threads=1,
    )

    assert result.returncode == 0, result.stderr
    assert output_file.exists()

    metadata = FFprobeRunner().probe(str(output_file))
    assert metadata["format_name"].startswith("mov")
    assert metadata["video"]["codec"] == "h264"
    assert metadata["video"]["width"] == 640
    assert metadata["video"]["height"] == 360

    atoms = top_level_mp4_atoms(output_file)
    assert "moov" in atoms and "mdat" in atoms
    assert atoms.index("moov") < atoms.index("mdat")


@pytest.mark.real_media
def test_convert_webm_to_mp4_real_fixture(tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / "converted_from_webm.mp4"

    result = FFmpegRunner().convert(
        str(media["video_webm_vp9_1080p"]),
        str(output_file),
        video_codec="libx264",
        audio_codec="aac",
        threads=1,
    )

    assert result.returncode == 0, result.stderr
    assert output_file.exists()

    metadata = FFprobeRunner().probe(str(output_file))
    assert metadata["video"]["codec"] == "h264"
    assert metadata["video"]["width"] == 1920
    assert metadata["video"]["height"] == 1080
    assert metadata["audio"]["codec"] == "aac"


@pytest.mark.real_media
def test_convert_audio_only_real_fixture(tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / "audio_only.mp3"

    result = FFmpegRunner().convert(
        str(media["video_mp4_h264_1080p"]),
        str(output_file),
        audio_only=True,
        audio_codec="libmp3lame",
        audio_bitrate="128k",
    )

    assert result.returncode == 0, result.stderr
    assert output_file.exists()

    metadata = FFprobeRunner().probe(str(output_file))
    assert "video" not in metadata
    assert metadata["audio"]["codec"] == "mp3"


@pytest.mark.real_media
def test_convert_selects_first_av_streams_and_preserves_unicode_metadata_and_chapters(tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / "selected.mp4"

    result = FFmpegRunner().convert(
        str(media["rich_streams_mkv"]),
        str(output_file),
        video_codec="libx264",
        audio_codec="aac",
        threads=1,
    )

    assert result.succeeded, result.stderr
    metadata = FFprobeRunner().probe_media(str(output_file))
    stream_types = [stream.codec_type for stream in metadata.streams]
    assert stream_types.count("video") == 1
    assert stream_types.count("audio") == 1
    assert "subtitle" not in stream_types
    assert next(stream for stream in metadata.streams if stream.codec_type == "audio").language == "eng"
    assert metadata.tags["title"] == "Résumé – 東京"
    assert [chapter["title"] for chapter in metadata.chapters] == ["Début", "Fin"]
