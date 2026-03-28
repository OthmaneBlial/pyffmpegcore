"""
Lightweight real-media smoke coverage for shipped example scripts.
"""

from __future__ import annotations

import shutil

import pytest

from examples import (
    compress_with_progress,
    convert_video,
    extract_metadata,
    extract_thumbnail,
    generate_waveform,
)
from pyffmpegcore import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


def _probe(path: str) -> dict:
    return FFprobeRunner().probe(path)


@pytest.mark.real_media
def test_convert_video_main_smoke_real_media(tmp_path, monkeypatch, capsys):
    media = ensure_downloaded_media()
    shutil.copy2(media["video_webm_vp9_1080p"], tmp_path / "input.avi")

    monkeypatch.chdir(tmp_path)
    convert_video.main()

    output_file = tmp_path / "output.mp4"
    assert output_file.exists()

    metadata = _probe(str(output_file))
    assert metadata["video"]["codec"] == "h264"
    assert metadata["audio"]["codec"] == "aac"
    assert "Conversion successful!" in capsys.readouterr().out


@pytest.mark.real_media
def test_extract_metadata_main_smoke_real_media(tmp_path, monkeypatch, capsys):
    media = ensure_downloaded_media()
    shutil.copy2(media["video_mp4_h264_1080p"], tmp_path / "sample.mp4")

    monkeypatch.chdir(tmp_path)
    extract_metadata.main()

    output = capsys.readouterr().out
    assert "File Metadata:" in output
    assert "Video Stream:" in output
    assert "Audio Stream:" in output
    assert "Resolution: (1920, 1080)" in output


@pytest.mark.real_media
def test_compress_with_progress_main_smoke_real_media(tmp_path, monkeypatch, capsys):
    media = ensure_downloaded_media()
    input_file = tmp_path / "input.mp4"
    shutil.copy2(media["video_mp4_h264_1080p"], input_file)

    monkeypatch.chdir(tmp_path)
    compress_with_progress.main()

    output_file = tmp_path / "compressed.mp4"
    assert output_file.exists()
    assert output_file.stat().st_size < input_file.stat().st_size
    assert "Compression successful!" in capsys.readouterr().out


@pytest.mark.real_media
def test_extract_thumbnail_example_smoke_real_media(tmp_path):
    media = ensure_downloaded_media()
    input_file = str(media["video_mp4_h264_1080p"])

    single_output = tmp_path / "single.jpg"
    multiple_output_dir = tmp_path / "multiple"
    smart_output_dir = tmp_path / "smart"

    assert extract_thumbnail.extract_thumbnail(
        input_file,
        str(single_output),
        timestamp="00:00:01",
        width=320,
    ) is True

    extract_thumbnail.extract_multiple_thumbnails(
        input_file,
        str(multiple_output_dir),
        ["00:00:00", "00:00:01"],
        width=240,
    )
    extract_thumbnail.extract_smart_thumbnails(
        input_file,
        str(smart_output_dir),
        count=2,
        width=200,
    )

    assert single_output.exists()
    assert len(list(multiple_output_dir.glob("*.jpg"))) == 2
    assert len(list(smart_output_dir.glob("*.jpg"))) == 2


@pytest.mark.real_media
def test_generate_waveform_example_smoke_real_media(tmp_path):
    media = ensure_downloaded_media()
    audio_input = str(media["audio_mp3"])
    basic_output = tmp_path / "wave.png"
    detailed_output = tmp_path / "wave_detail.png"
    animation_output = tmp_path / "wave_anim.mp4"
    metadata_output_dir = tmp_path / "wave_meta"

    assert generate_waveform.generate_waveform_image(
        audio_input,
        str(basic_output),
        width=800,
        height=200,
    ) is True
    assert generate_waveform.generate_detailed_waveform(
        audio_input,
        str(detailed_output),
        width=900,
        height=240,
    ) is True
    assert generate_waveform.generate_waveform_animation(
        audio_input,
        str(animation_output),
        duration=2,
        width=640,
        height=160,
    ) is True
    assert generate_waveform.generate_waveform_with_metadata(
        audio_input,
        str(metadata_output_dir),
    ) is True

    basic_metadata = _probe(str(basic_output))
    detailed_metadata = _probe(str(detailed_output))
    animation_metadata = _probe(str(animation_output))

    assert basic_metadata["video"]["codec"] == "png"
    assert detailed_metadata["video"]["codec"] == "png"
    assert animation_metadata["video"]["codec"] == "h264"
    assert (metadata_output_dir / "sample_audio_mp3_waveform.png").exists()
    assert (metadata_output_dir / "sample_audio_mp3_waveform_with_metadata.png").exists()
