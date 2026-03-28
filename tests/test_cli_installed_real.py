"""
Real-media integration tests for the installed pyffmpegcore command.
"""

from __future__ import annotations

import hashlib
import json
import shutil

import pytest

from pyffmpegcore import FFmpegRunner
from pyffmpegcore.probe import FFprobeRunner
from tests.cli_helpers import run_installed_cli
from tests.media_utils import ensure_downloaded_media


SHORT_SRT = """1
00:00:00,000 --> 00:00:02,500
Welcome to the installed CLI subtitle file!

2
00:00:03,000 --> 00:00:05,500
This subtitle line is used for installed CLI validation.
"""


def _probe_streams(path: str) -> list[dict]:
    result = run_installed_cli(
        "probe",
        "--input",
        path,
        "--json",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    streams: list[dict] = []
    if payload.get("video"):
        streams.append({"codec_type": "video", "codec_name": payload["video"]["codec"]})
    if payload.get("audio"):
        streams.append({"codec_type": "audio", "codec_name": payload["audio"]["codec"]})
    if payload.get("subtitle"):
        streams.append({"codec_type": "subtitle", "codec_name": payload["subtitle"]["codec"]})
    return streams


@pytest.mark.real_media
def test_installed_cli_doctor_and_probe_real_media():
    """
    The installed command should expose diagnostics plus human and JSON probe modes.
    """
    media = ensure_downloaded_media()

    doctor = run_installed_cli("doctor", "--json")
    assert doctor.returncode == 0
    doctor_payload = json.loads(doctor.stdout)
    assert doctor_payload["ffmpeg"]["available"] is True
    assert doctor_payload["ffprobe"]["available"] is True

    probe_human = run_installed_cli("probe", "--input", str(media["video_mp4_h264_1080p"]))
    assert probe_human.returncode == 0
    assert "Video stream:" in probe_human.stdout
    assert "Audio stream:" in probe_human.stdout

    probe_json = run_installed_cli(
        "probe",
        "--input",
        str(media["audio_mp3"]),
        "--json",
    )
    assert probe_json.returncode == 0
    probe_payload = json.loads(probe_json.stdout)
    assert probe_payload["audio"]["codec"] == "mp3"


@pytest.mark.real_media
def test_installed_cli_core_video_commands_real_media(tmp_path):
    """
    The installed command should handle the main convert, compress, extract, thumbnail, and waveform jobs.
    """
    media = ensure_downloaded_media()
    converted = tmp_path / "converted.mp4"
    compressed = tmp_path / "compressed.mp4"
    audio_only = tmp_path / "audio-only.mp3"
    thumbnail = tmp_path / "thumbnail.jpg"
    waveform = tmp_path / "waveform.png"

    convert = run_installed_cli(
        "convert",
        "--input",
        str(media["video_webm_vp9_1080p"]),
        "--output",
        str(converted),
        "--video-codec",
        "libx264",
        "--audio-codec",
        "aac",
    )
    assert convert.returncode == 0
    assert "Output:" in convert.stdout
    assert FFprobeRunner().probe(str(converted))["video"]["codec"] == "h264"

    compress = run_installed_cli(
        "compress",
        "--input",
        str(media["video_mp4_h264_1080p"]),
        "--output",
        str(compressed),
        "--crf",
        "28",
    )
    assert compress.returncode == 0
    assert compressed.exists()

    extract = run_installed_cli(
        "extract-audio",
        "--input",
        str(media["video_mp4_h264_1080p"]),
        "--output",
        str(audio_only),
    )
    assert extract.returncode == 0
    assert FFprobeRunner().probe(str(audio_only))["audio"]["codec"] == "mp3"

    thumbnail_result = run_installed_cli(
        "thumbnail",
        "--input",
        str(media["video_mp4_h264_1080p"]),
        "--output",
        str(thumbnail),
        "--timestamp",
        "00:00:01",
        "--width",
        "640",
    )
    assert thumbnail_result.returncode == 0
    assert thumbnail.exists()

    waveform_result = run_installed_cli(
        "waveform",
        "--input",
        str(media["audio_mp3"]),
        "--output",
        str(waveform),
        "--width",
        "1200",
        "--height",
        "300",
    )
    assert waveform_result.returncode == 0
    assert waveform.exists()


@pytest.mark.real_media
def test_installed_cli_speed_and_concat_real_media(tmp_path):
    """
    The installed command should support speed changes plus both concat modes.
    """
    media = ensure_downloaded_media()
    fast_video = tmp_path / "fast-video.mp4"
    fast_audio = tmp_path / "fast-audio.mp3"
    copy_a = tmp_path / "clip one's source.mp4"
    copy_b = tmp_path / "clip two source.mp4"
    joined_copy = tmp_path / "joined-copy.mp4"
    joined_reencode = tmp_path / "joined-reencode.mp4"

    speed_video = run_installed_cli(
        "speed",
        "video",
        "--input",
        str(media["video_mp4_h264_1080p"]),
        "--output",
        str(fast_video),
        "--factor",
        "1.5",
    )
    assert speed_video.returncode == 0
    assert FFprobeRunner().get_duration(str(fast_video)) < FFprobeRunner().get_duration(
        str(media["video_mp4_h264_1080p"])
    )

    speed_audio = run_installed_cli(
        "speed",
        "audio",
        "--input",
        str(media["audio_mp3"]),
        "--output",
        str(fast_audio),
        "--factor",
        "1.25",
    )
    assert speed_audio.returncode == 0
    assert FFprobeRunner().probe(str(fast_audio))["audio"]["codec"] == "mp3"

    shutil.copy2(media["video_mp4_h264_1080p"], copy_a)
    shutil.copy2(media["video_mp4_h264_1080p"], copy_b)
    concat_copy = run_installed_cli(
        "concat",
        "--mode",
        "copy",
        "--inputs",
        str(copy_a),
        str(copy_b),
        "--output",
        str(joined_copy),
    )
    assert concat_copy.returncode == 0
    assert joined_copy.exists()

    concat_reencode = run_installed_cli(
        "concat",
        "--mode",
        "reencode",
        "--inputs",
        str(media["video_mp4_h264_1080p"]),
        str(media["video_webm_vp9_1080p"]),
        "--output",
        str(joined_reencode),
    )
    assert concat_reencode.returncode == 0
    joined_reencode_probe = FFprobeRunner().probe(str(joined_reencode))
    assert joined_reencode_probe["video"]["codec"] == "h264"
    assert joined_reencode_probe["audio"]["codec"] == "aac"


@pytest.mark.real_media
def test_installed_cli_subtitles_real_media(tmp_path):
    """
    The installed command should add, extract, and burn subtitles on real media.
    """
    media = ensure_downloaded_media()
    subtitle_file = tmp_path / "external subtitles.srt"
    subtitle_file.write_text(SHORT_SRT, encoding="utf-8")
    muxed_output = tmp_path / "with-subtitles.mp4"
    extracted_output = tmp_path / "extracted.srt"
    burned_output = tmp_path / "burned.mp4"
    original_frame = tmp_path / "original-frame.jpg"
    burned_frame = tmp_path / "burned-frame.jpg"

    added = run_installed_cli(
        "subtitles",
        "add",
        "--video",
        str(media["video_mp4_h264_1080p"]),
        "--subtitle",
        str(subtitle_file),
        "--output",
        str(muxed_output),
        "--language",
        "eng",
    )
    assert added.returncode == 0
    assert muxed_output.exists()

    extracted = run_installed_cli(
        "subtitles",
        "extract",
        "--video",
        str(muxed_output),
        "--output",
        str(extracted_output),
    )
    assert extracted.returncode == 0
    extracted_text = extracted_output.read_text(encoding="utf-8")
    assert "installed CLI subtitle file" in extracted_text

    burned = run_installed_cli(
        "subtitles",
        "burn",
        "--video",
        str(media["video_mp4_h264_1080p"]),
        "--subtitle",
        str(subtitle_file),
        "--output",
        str(burned_output),
    )
    assert burned.returncode == 0
    assert _probe_streams(str(burned_output)) == [
        {"codec_type": "video", "codec_name": "h264"},
        {"codec_type": "audio", "codec_name": "aac"},
    ]

    runner = FFmpegRunner()
    assert runner.extract_thumbnail(
        str(media["video_mp4_h264_1080p"]),
        str(original_frame),
        timestamp="00:00:01.000",
        width=960,
    ).returncode == 0
    assert runner.extract_thumbnail(
        str(burned_output),
        str(burned_frame),
        timestamp="00:00:01.000",
        width=960,
    ).returncode == 0
    assert hashlib.sha256(original_frame.read_bytes()).hexdigest() != hashlib.sha256(
        burned_frame.read_bytes()
    ).hexdigest()


@pytest.mark.real_media
def test_installed_cli_audio_workflows_real_media(tmp_path):
    """
    The installed command should support every public audio workflow command.
    """
    media = ensure_downloaded_media()
    mixed_output = tmp_path / "mixed.mp3"
    merged_output = tmp_path / "merged.mp3"
    mashup_output = tmp_path / "mashup.mp3"
    background_output = tmp_path / "background.mp3"
    normalized_output = tmp_path / "normalized.mp3"

    mixed = run_installed_cli(
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
    )
    assert mixed.returncode == 0

    merged = run_installed_cli(
        "mix-audio",
        "concat",
        "--inputs",
        str(media["audio_mp3"]),
        str(media["audio_wav_pcm"]),
        "--output",
        str(merged_output),
    )
    assert merged.returncode == 0

    mashup = run_installed_cli(
        "mix-audio",
        "mashup",
        "--inputs",
        str(media["audio_mp3"]),
        str(media["audio_wav_pcm"]),
        "--output",
        str(mashup_output),
        "--crossfade-duration",
        "0.5",
    )
    assert mashup.returncode == 0

    background = run_installed_cli(
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
    )
    assert background.returncode == 0

    normalized = run_installed_cli(
        "normalize-audio",
        "--input",
        str(media["audio_mp3"]),
        "--output",
        str(normalized_output),
        "--method",
        "loudnorm",
    )
    assert normalized.returncode == 0

    for path in (
        mixed_output,
        merged_output,
        mashup_output,
        background_output,
        normalized_output,
    ):
        assert FFprobeRunner().probe(str(path))["audio"]["codec"] == "mp3"


@pytest.mark.real_media
def test_installed_cli_image_workflows_real_media(tmp_path):
    """
    The installed command should support every public image workflow command.
    """
    media = ensure_downloaded_media()
    input_dir = tmp_path / "input"
    jpg_dir = tmp_path / "jpg"
    optimized_dir = tmp_path / "optimized"
    webp_dir = tmp_path / "webp"
    input_dir.mkdir()
    shutil.copy2(media["image_png"], input_dir / "sample one.png")
    shutil.copy2(media["image_jpg"], input_dir / "sample two.jpg")
    (input_dir / "broken.png").write_text("not an image", encoding="utf-8")

    converted = run_installed_cli(
        "images",
        "convert",
        "--input-dir",
        str(input_dir),
        "--output-dir",
        str(jpg_dir),
        "--format",
        "jpg",
    )
    assert converted.returncode == 6
    assert (jpg_dir / "sample one.jpg").exists()

    optimized = run_installed_cli(
        "images",
        "optimize",
        "--input-dir",
        str(input_dir),
        "--output-dir",
        str(optimized_dir),
        "--max-width",
        "320",
        "--max-height",
        "240",
    )
    assert optimized.returncode == 6
    optimized_probe = FFprobeRunner().probe(str(optimized_dir / "sample two.jpg"))
    assert optimized_probe["video"]["width"] <= 320
    assert optimized_probe["video"]["height"] <= 240

    webp = run_installed_cli(
        "images",
        "webp",
        "--input-dir",
        str(input_dir),
        "--output-dir",
        str(webp_dir),
        "--quality",
        "80",
    )
    assert webp.returncode == 6
    assert (webp_dir / "sample one.webp").exists()
