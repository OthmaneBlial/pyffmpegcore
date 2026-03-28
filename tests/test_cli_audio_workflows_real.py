"""
Real-media tests for CLI audio workflow commands.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from pyffmpegcore.probe import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_mix_audio_mix_and_concat_real_media(tmp_path):
    """
    The CLI should mix and concatenate real audio fixtures into playable outputs.
    """
    media = ensure_downloaded_media()
    mixed_output = tmp_path / "mixed.mp3"
    merged_output = tmp_path / "merged.mp3"

    mixed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "mix-audio",
            "mix",
            "--inputs",
            str(media["audio_mp3"]),
            str(media["audio_wav_pcm"]),
            "--output",
            str(mixed_output),
            "--volumes",
            "1.0",
            "0.4",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    merged = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "mix-audio",
            "concat",
            "--inputs",
            str(media["audio_mp3"]),
            str(media["audio_wav_pcm"]),
            "--output",
            str(merged_output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert mixed.returncode == 0
    assert merged.returncode == 0
    assert FFprobeRunner().probe(str(mixed_output))["audio"]["codec"] == "mp3"
    assert FFprobeRunner().probe(str(merged_output))["audio"]["codec"] == "mp3"


@pytest.mark.real_media
def test_mix_audio_background_and_mashup_real_media(tmp_path):
    """
    The CLI should support background layering and mashup crossfades on real audio fixtures.
    """
    media = ensure_downloaded_media()
    background_output = tmp_path / "background.mp3"
    mashup_output = tmp_path / "mashup.mp3"

    background = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "mix-audio",
            "background",
            "--main-input",
            str(media["audio_mp3"]),
            "--background-input",
            str(media["audio_wav_pcm"]),
            "--output",
            str(background_output),
            "--bg-volume",
            "0.25",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    mashup = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "mix-audio",
            "mashup",
            "--inputs",
            str(media["audio_mp3"]),
            str(media["audio_wav_pcm"]),
            "--output",
            str(mashup_output),
            "--crossfade-duration",
            "0.5",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert background.returncode == 0
    assert mashup.returncode == 0
    assert FFprobeRunner().probe(str(background_output))["audio"]["codec"] == "mp3"
    assert FFprobeRunner().probe(str(mashup_output))["audio"]["codec"] == "mp3"


@pytest.mark.real_media
def test_normalize_audio_real_media(tmp_path):
    """
    The CLI should support both loudnorm and mastering-oriented outputs.
    """
    media = ensure_downloaded_media()
    normalized_output = tmp_path / "normalized.mp3"
    mastered_output = tmp_path / "mastered.mp3"

    normalized = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "normalize-audio",
            "--input",
            str(media["audio_mp3"]),
            "--output",
            str(normalized_output),
            "--method",
            "loudnorm",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    mastered = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "normalize-audio",
            "--input",
            str(media["video_mp4_h264_1080p"]),
            "--output",
            str(mastered_output),
            "--method",
            "master",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert normalized.returncode == 0
    assert mastered.returncode == 0
    assert FFprobeRunner().probe(str(normalized_output))["audio"]["codec"] == "mp3"
    assert FFprobeRunner().probe(str(mastered_output))["audio"]["codec"] == "mp3"
