"""
Real-media tests for the CLI thumbnail command.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from pyffmpegcore.probe import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
@pytest.mark.parametrize(
    ("timestamp", "width", "height"),
    [
        ("00:00:00.100", 320, None),
        ("00:00:05.200", 200, 120),
    ],
)
def test_thumbnail_real_media(tmp_path, timestamp, width, height):
    """
    The thumbnail command should create readable images from the validated MP4 fixture.
    """
    media = ensure_downloaded_media()
    output_file = tmp_path / f"thumb-{width}-{height or 'auto'}.jpg"

    command = [
        sys.executable,
        "-m",
        "pyffmpegcore",
        "thumbnail",
        "--input",
        str(media["video_mp4_h264_1080p"]),
        "--output",
        str(output_file),
        "--timestamp",
        timestamp,
        "--width",
        str(width),
    ]
    if height is not None:
        command.extend(["--height", str(height)])

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert output_file.exists()
    metadata = FFprobeRunner().probe(str(output_file))
    assert metadata["video"]["codec"] == "mjpeg"
    assert metadata["video"]["width"] == width
    if height is not None:
        assert metadata["video"]["height"] == height


@pytest.mark.real_media
def test_thumbnail_recipe_proves_dimensions_receipt_and_force(tmp_path):
    """The documented recipe exposes machine-readable proof and safe overwrite behavior."""
    media = ensure_downloaded_media()
    output_file = tmp_path / "thumbnail.jpg"
    receipt_file = tmp_path / "thumbnail.receipt.json"

    command = [
        sys.executable,
        "-m",
        "pyffmpegcore",
        "thumbnail",
        "--input",
        str(media["video_mp4_h264_1080p"]),
        "--output",
        str(output_file),
        "--timestamp",
        "00:00:01",
        "--width",
        "640",
        "--receipt",
        str(receipt_file),
        "--result-json",
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
    result_payload = json.loads(result.stdout)
    assert result_payload["summary"]["succeeded"] == 1

    probe = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "probe",
            "--input",
            str(output_file),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert probe.returncode == 0, probe.stderr
    output_metadata = json.loads(probe.stdout)
    assert output_metadata["video"]["codec"] == "mjpeg"
    assert output_metadata["video"]["width"] == 640
    assert receipt_file.exists()
    assert str(tmp_path) not in receipt_file.read_text(encoding="utf-8")

    validation = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "receipt",
            "validate",
            str(receipt_file),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert validation.returncode == 0, validation.stderr
    assert json.loads(validation.stdout)["valid"] is True

    refused = subprocess.run(command, capture_output=True, text=True, check=False)
    assert refused.returncode == 4
    assert "Re-run with --force to overwrite" in refused.stderr

    forced = subprocess.run(
        [*command, "--force"], capture_output=True, text=True, check=False
    )
    assert forced.returncode == 0, forced.stderr
