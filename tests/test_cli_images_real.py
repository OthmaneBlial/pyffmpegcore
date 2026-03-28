"""
Real-media tests for CLI image workflow commands.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

import pytest

from pyffmpegcore.probe import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_images_convert_real_media_reports_partial_failure(tmp_path):
    """
    The CLI should convert valid images and return a partial-success exit code for broken inputs.
    """
    media = ensure_downloaded_media()
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    shutil.copy2(media["image_png"], input_dir / "sample one.png")
    shutil.copy2(media["image_jpg"], input_dir / "sample two.jpg")
    (input_dir / "broken.png").write_text("not an image", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "images",
            "convert",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--format",
            "jpg",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 6
    assert (output_dir / "sample one.jpg").exists()
    assert (output_dir / "sample two.jpg").exists()


@pytest.mark.real_media
def test_images_optimize_real_media_resizes_large_images(tmp_path):
    """
    The optimize command should resize oversized inputs and keep partial-failure behavior.
    """
    media = ensure_downloaded_media()
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "optimized"
    input_dir.mkdir()
    shutil.copy2(media["image_png"], input_dir / "sample one.png")
    shutil.copy2(media["image_jpg"], input_dir / "sample two.jpg")
    (input_dir / "broken.png").write_text("not an image", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "images",
            "optimize",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--max-width",
            "320",
            "--max-height",
            "240",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 6
    optimized = FFprobeRunner().probe(str(output_dir / "sample two.jpg"))
    assert optimized["video"]["width"] <= 320
    assert optimized["video"]["height"] <= 240


@pytest.mark.real_media
def test_images_webp_real_media_reports_partial_failure(tmp_path):
    """
    The WebP conversion command should convert valid images and report broken inputs cleanly.
    """
    media = ensure_downloaded_media()
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "webp"
    input_dir.mkdir()
    shutil.copy2(media["image_png"], input_dir / "sample one.png")
    shutil.copy2(media["image_jpg"], input_dir / "sample two.jpg")
    (input_dir / "broken.png").write_text("not an image", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyffmpegcore",
            "images",
            "webp",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 6
    assert (output_dir / "sample one.webp").exists()
    assert (output_dir / "sample two.webp").exists()
