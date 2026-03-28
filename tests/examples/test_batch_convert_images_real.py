"""
Real-media coverage for the batch_convert_images example.
"""

from __future__ import annotations

import shutil

import pytest

from examples.batch_convert_images import (
    batch_convert_images,
    convert_image,
    convert_to_webp_batch,
    optimize_images_for_web,
)
from pyffmpegcore import FFprobeRunner
from tests.media_utils import ensure_downloaded_media


def _probe(path: str) -> dict:
    return FFprobeRunner().probe(path)


@pytest.mark.real_media
def test_convert_image_real_media_resizes_png_to_webp(tmp_path):
    media = ensure_downloaded_media()
    output_file = tmp_path / "converted.webp"

    converted = convert_image(
        str(media["image_png"]),
        str(output_file),
        quality=75,
        resize=(200, 150),
    )

    assert converted is True
    assert output_file.exists()

    metadata = _probe(str(output_file))
    assert metadata["video"]["codec"] == "webp"
    assert metadata["video"]["width"] == 200
    assert metadata["video"]["height"] == 150


@pytest.mark.real_media
def test_batch_convert_images_real_media_reports_broken_files(tmp_path):
    media = ensure_downloaded_media()
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "outputs"
    input_dir.mkdir()

    shutil.copy2(media["image_png"], input_dir / "sample one.png")
    shutil.copy2(media["image_jpg"], input_dir / "sample two.jpg")
    (input_dir / "broken.png").write_text("not an image", encoding="utf-8")

    results = batch_convert_images(
        str(input_dir),
        str(output_dir),
        output_format="jpg",
        quality=80,
        max_workers=2,
    )

    assert results == {"total": 3, "successful": 2, "failed": 1}

    first_output = output_dir / "sample one.jpg"
    second_output = output_dir / "sample two.jpg"
    assert first_output.exists()
    assert second_output.exists()

    first_input_metadata = _probe(str(input_dir / "sample one.png"))
    second_input_metadata = _probe(str(input_dir / "sample two.jpg"))
    first_metadata = _probe(str(first_output))
    second_metadata = _probe(str(second_output))
    assert first_metadata["video"]["codec"] == "mjpeg"
    assert second_metadata["video"]["codec"] == "mjpeg"
    assert first_metadata["video"]["width"] == first_input_metadata["video"]["width"]
    assert first_metadata["video"]["height"] == first_input_metadata["video"]["height"]
    assert second_metadata["video"]["width"] == second_input_metadata["video"]["width"]
    assert second_metadata["video"]["height"] == second_input_metadata["video"]["height"]


@pytest.mark.real_media
def test_optimize_images_for_web_real_media_resizes_oversized_inputs(tmp_path):
    media = ensure_downloaded_media()
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "web"
    input_dir.mkdir()

    shutil.copy2(media["image_png"], input_dir / "sample one.png")
    shutil.copy2(media["image_jpg"], input_dir / "sample two.jpg")
    (input_dir / "broken.png").write_text("not an image", encoding="utf-8")

    results = optimize_images_for_web(
        str(input_dir),
        str(output_dir),
        max_width=320,
        max_height=240,
        quality=80,
    )

    assert results == {"total": 3, "successful": 2, "failed": 1}

    first_metadata = _probe(str(output_dir / "sample one.jpg"))
    second_metadata = _probe(str(output_dir / "sample two.jpg"))
    assert first_metadata["video"]["width"] == 200
    assert first_metadata["video"]["height"] == 150
    assert second_metadata["video"]["width"] == 320
    assert second_metadata["video"]["height"] == 213


@pytest.mark.real_media
def test_convert_to_webp_batch_real_media_reports_broken_files(tmp_path):
    media = ensure_downloaded_media()
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "webp"
    input_dir.mkdir()

    shutil.copy2(media["image_png"], input_dir / "sample one.png")
    shutil.copy2(media["image_jpg"], input_dir / "sample two.jpg")
    (input_dir / "broken.png").write_text("not an image", encoding="utf-8")

    results = convert_to_webp_batch(
        str(input_dir),
        str(output_dir),
        quality=70,
    )

    assert results == {"total": 3, "successful": 2, "failed": 1}

    first_input_metadata = _probe(str(input_dir / "sample one.png"))
    second_input_metadata = _probe(str(input_dir / "sample two.jpg"))
    first_metadata = _probe(str(output_dir / "sample one.webp"))
    second_metadata = _probe(str(output_dir / "sample two.webp"))
    assert first_metadata["video"]["codec"] == "webp"
    assert second_metadata["video"]["codec"] == "webp"
    assert first_metadata["video"]["width"] == first_input_metadata["video"]["width"]
    assert first_metadata["video"]["height"] == first_input_metadata["video"]["height"]
    assert second_metadata["video"]["width"] == second_input_metadata["video"]["width"]
    assert second_metadata["video"]["height"] == second_input_metadata["video"]["height"]
