"""
Real-media coverage for mix_audio.py and normalize_audio.py examples.
"""

from __future__ import annotations

import re
import subprocess

import pytest

from examples.mix_audio import (
    add_background_music,
    create_audio_mashup,
    merge_audio_sequentially,
    mix_audio_files,
)
from examples.normalize_audio import create_mastered_audio, normalize_audio_loudnorm
from pyffmpegcore import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


def _probe(path: str) -> dict:
    return FFprobeRunner().probe(path)


def _decode_ok(path: str) -> bool:
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _volume_levels(path: str) -> tuple[float, float]:
    result = subprocess.run(
        ["ffmpeg", "-i", path, "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    mean_match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?) dB", result.stderr)
    max_match = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?) dB", result.stderr)
    assert mean_match is not None
    assert max_match is not None
    return float(mean_match.group(1)), float(max_match.group(1))


@pytest.mark.real_media
def test_mix_and_merge_audio_real_media(tmp_path):
    media = ensure_downloaded_media()
    first_input = str(media["audio_mp3"])
    second_input = str(media["audio_wav_pcm"])
    mixed_output = tmp_path / "mixed.mp3"
    merged_output = tmp_path / "merged.mp3"

    mixed = mix_audio_files(
        [first_input, second_input],
        str(mixed_output),
        volumes=[1.0, 0.4],
    )
    merged = merge_audio_sequentially(
        [first_input, second_input],
        str(merged_output),
    )

    assert mixed is True
    assert merged is True
    assert mixed_output.exists()
    assert merged_output.exists()
    assert _decode_ok(str(mixed_output))
    assert _decode_ok(str(merged_output))

    first_metadata = _probe(first_input)
    second_metadata = _probe(second_input)
    mixed_metadata = _probe(str(mixed_output))
    merged_metadata = _probe(str(merged_output))

    assert mixed_metadata["audio"]["codec"] == "mp3"
    assert merged_metadata["audio"]["codec"] == "mp3"
    expected_mixed_duration = max(first_metadata["duration"], second_metadata["duration"])
    expected_merged_duration = first_metadata["duration"] + second_metadata["duration"]
    assert mixed_metadata["duration"] == pytest.approx(expected_mixed_duration, abs=0.35)
    assert merged_metadata["duration"] == pytest.approx(expected_merged_duration, abs=0.35)


@pytest.mark.real_media
def test_background_music_and_mashup_real_media(tmp_path):
    media = ensure_downloaded_media()
    main_input = str(media["video_mp4_h264_1080p"])
    background_input = str(media["audio_mp3"])
    secondary_input = str(media["audio_wav_pcm"])
    background_output = tmp_path / "with_background.mp3"
    mashup_output = tmp_path / "mashup.mp3"

    background_mixed = add_background_music(
        main_input,
        background_input,
        str(background_output),
        bg_volume=0.2,
    )
    mashup = create_audio_mashup(
        [background_input, secondary_input],
        str(mashup_output),
        crossfade_duration=1.0,
    )

    assert background_mixed is True
    assert mashup is True
    assert background_output.exists()
    assert mashup_output.exists()
    assert _decode_ok(str(background_output))
    assert _decode_ok(str(mashup_output))

    main_metadata = _probe(main_input)
    first_audio_metadata = _probe(background_input)
    second_audio_metadata = _probe(secondary_input)
    background_metadata = _probe(str(background_output))
    mashup_metadata = _probe(str(mashup_output))

    assert background_metadata["audio"]["codec"] == "mp3"
    assert mashup_metadata["audio"]["codec"] == "mp3"
    assert background_metadata["duration"] == pytest.approx(main_metadata["duration"], abs=0.35)
    expected_mashup_duration = (
        first_audio_metadata["duration"] + second_audio_metadata["duration"] - 1.0
    )
    assert mashup_metadata["duration"] == pytest.approx(expected_mashup_duration, abs=0.5)


@pytest.mark.real_media
def test_normalize_and_master_audio_real_media(tmp_path):
    media = ensure_downloaded_media()
    audio_input = str(media["audio_mp3"])
    video_input = str(media["video_mp4_h264_1080p"])
    normalized_output = tmp_path / "normalized.mp3"
    mastered_output = tmp_path / "mastered.mp3"

    normalized = normalize_audio_loudnorm(audio_input, str(normalized_output))
    mastered = create_mastered_audio(video_input, str(mastered_output))

    assert normalized is True
    assert mastered is True
    assert normalized_output.exists()
    assert mastered_output.exists()
    assert _decode_ok(str(normalized_output))
    assert _decode_ok(str(mastered_output))

    input_audio_metadata = _probe(audio_input)
    input_video_metadata = _probe(video_input)
    normalized_metadata = _probe(str(normalized_output))
    mastered_metadata = _probe(str(mastered_output))

    assert normalized_metadata["audio"]["codec"] == "mp3"
    assert mastered_metadata["audio"]["codec"] == "mp3"
    assert normalized_metadata["duration"] == pytest.approx(input_audio_metadata["duration"], abs=0.35)
    assert mastered_metadata["duration"] == pytest.approx(input_video_metadata["duration"], abs=0.35)

    source_mean, source_max = _volume_levels(audio_input)
    normalized_mean, normalized_max = _volume_levels(str(normalized_output))
    video_mean, _video_max = _volume_levels(video_input)
    mastered_mean, mastered_max = _volume_levels(str(mastered_output))

    assert abs(normalized_mean - source_mean) >= 2.0
    assert abs(normalized_max - source_max) >= 2.0
    assert abs(mastered_mean - video_mean) >= 2.0
    assert mastered_max <= -0.5
