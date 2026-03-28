"""
Real-media tests for single-pass FFmpegRunner.compress().
"""

from __future__ import annotations

import json
import subprocess

import pytest

from pyffmpegcore import FFmpegRunner, FFprobeRunner
from tests.media_utils import ensure_downloaded_media
from tests.mp4_utils import top_level_mp4_atoms


def _probe_video_stream(path: str) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,pix_fmt",
            "-of",
            "json",
            path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["streams"][0]


@pytest.mark.real_media
def test_single_pass_compress_real_fixture_reduces_size(tmp_path):
    media = ensure_downloaded_media()
    input_file = media["video_mov_h264_640x360"]
    output_file = tmp_path / "compressed_single_pass.mp4"

    result = FFmpegRunner().compress(
        str(input_file),
        str(output_file),
        crf=32,
        preset="fast",
        threads=1,
    )

    assert result.returncode == 0, result.stderr
    assert output_file.exists()
    assert output_file.stat().st_size < input_file.stat().st_size

    metadata = FFprobeRunner().probe(str(output_file))
    assert metadata["video"]["codec"] == "h264"
    assert "audio" not in metadata

    video_stream = _probe_video_stream(str(output_file))
    assert video_stream["pix_fmt"] == "yuv420p"

    atoms = top_level_mp4_atoms(output_file)
    assert atoms.index("moov") < atoms.index("mdat")
