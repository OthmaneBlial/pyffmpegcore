"""
Real-media tests for the CLI concat command.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

import pytest

from pyffmpegcore.probe import FFprobeRunner
from tests.media_utils import ensure_downloaded_media, ffmpeg_has_encoder, ffmpeg_has_filter


@pytest.mark.real_media
def test_concat_copy_real_media_handles_special_paths(tmp_path):
    """
    Copy-mode concat should handle clips whose paths contain spaces and apostrophes.
    """
    media = ensure_downloaded_media()
    first_clip = tmp_path / "clip one's source.mp4"
    second_clip = tmp_path / "clip two source.mp4"
    shutil.copy2(media["video_mp4_h264_1080p"], first_clip)
    shutil.copy2(media["video_mp4_h264_1080p"], second_clip)
    output_file = tmp_path / "joined clip.mp4"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "concat",
            "--mode",
            "copy",
            "--inputs",
            str(first_clip),
            str(second_clip),
            "--output",
            str(output_file),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert output_file.exists()
    metadata = FFprobeRunner().probe(str(output_file))
    input_duration = FFprobeRunner().get_duration(str(media["video_mp4_h264_1080p"]))
    assert metadata["video"]["codec"] == "h264"
    assert metadata["duration"] == pytest.approx(input_duration * 2, abs=0.5)


@pytest.mark.real_media
def test_concat_reencode_real_media_mixed_formats(tmp_path):
    """
    Re-encode concat should join mixed MP4 and WebM inputs into a readable MP4 output.
    """
    media = ensure_downloaded_media()
    output_file = tmp_path / "joined-reencoded.mp4"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "concat",
            "--mode",
            "reencode",
            "--inputs",
            str(media["video_mp4_h264_1080p"]),
            str(media["video_webm_vp9_1080p"]),
            "--output",
            str(output_file),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert output_file.exists()
    metadata = FFprobeRunner().probe(str(output_file))
    assert metadata["video"]["codec"] == "h264"
    assert metadata["audio"]["codec"] == "aac"


@pytest.mark.real_media
def test_concat_reencode_normalizes_timestamps_and_audio_format(tmp_path):
    if not all(ffmpeg_has_filter(name) for name in ("concat", "setpts", "asetpts")):
        pytest.skip("Local FFmpeg build does not include the concat timestamp filters")
    if not all(ffmpeg_has_encoder(name) for name in ("mpeg4", "aac")):
        pytest.skip("Local FFmpeg build does not include the required native encoders")

    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mkv"
    incompatible = tmp_path / "smaller.mp4"
    for path, size, sample_rate, audio_codec, offset in (
        (first, "160x90", "48000", "aac", None),
        (second, "160x90", "44100", "pcm_s16le", "0.25"),
        (incompatible, "128x72", "48000", "aac", None),
    ):
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size={size}:rate=10:duration=0.5",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:sample_rate={sample_rate}:duration=0.5",
            "-shortest",
            "-c:v",
            "mpeg4",
            "-q:v",
            "8",
            "-c:a",
            audio_codec,
        ]
        if offset is not None:
            command.extend(["-output_ts_offset", offset])
        command.append(str(path))
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=20)

    copy_rejected_output = tmp_path / "copy-incompatible.mp4"
    copy_rejected = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "concat",
            "--mode",
            "copy",
            "--inputs",
            str(first),
            str(incompatible),
            "--output",
            str(copy_rejected_output),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert copy_rejected.returncode == 4
    assert "\n[FAIL] concat/copy-compatibility:" in copy_rejected.stderr
    assert not copy_rejected_output.exists()

    rejected_output = tmp_path / "incompatible.mp4"
    rejected = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "concat",
            "--mode",
            "reencode",
            "--inputs",
            str(first),
            str(incompatible),
            "--output",
            str(rejected_output),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert rejected.returncode == 4
    assert "\n[FAIL] concat/reencode-compatibility:" in rejected.stderr
    assert "\\n[FAIL]" not in rejected.stderr
    assert not rejected_output.exists()

    output = tmp_path / "joined.mp4"
    receipt = tmp_path / "joined.receipt.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "concat",
            "--mode",
            "reencode",
            "--video-codec",
            "mpeg4",
            "--audio-codec",
            "aac",
            "--inputs",
            str(first),
            str(second),
            "--output",
            str(output),
            "--receipt",
            str(receipt),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    metadata = FFprobeRunner().probe(str(output))
    assert metadata["video"]["codec"] == "mpeg4"
    assert metadata["audio"]["codec"] == "aac"
    assert metadata["duration"] == pytest.approx(1.0, abs=0.2)
    validation = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore", "receipt", "validate", str(receipt), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert validation.returncode == 0, validation.stderr
