"""Image examples are thin consumers of shared single and batch plans."""

from unittest.mock import MagicMock, patch

from examples.batch_convert_images import (
    batch_convert_images,
    convert_image,
    convert_to_webp_batch,
    optimize_images_for_web,
)


def _engine(*, succeeded: int = 2, failed: int = 0):
    engine = MagicMock()
    engine.run.return_value = MagicMock(
        succeeded=failed == 0,
        succeeded_count=succeeded,
        failed_count=failed,
        items=tuple(MagicMock(succeeded=True) for _ in range(succeeded + failed)),
    )
    return engine


@patch("examples.batch_convert_images.WorkflowEngine")
def test_convert_image_uses_shared_single_image_plan(engine_type):
    engine = _engine(succeeded=1)
    engine_type.return_value = engine

    assert convert_image("input.png", "output.jpg", quality=85, resize=(200, 100)) is True
    engine.planner.image.assert_called_once_with(
        "input.png",
        "output.jpg",
        quality=85,
        resize=(200, 100),
    )


@patch("examples.batch_convert_images.WorkflowEngine")
def test_batch_convert_images_returns_shared_batch_counts(engine_type):
    engine = _engine(succeeded=2, failed=1)
    engine_type.return_value = engine

    results = batch_convert_images("input", "output", output_format="jpg", quality=80)

    assert results == {"total": 3, "successful": 2, "failed": 1}
    engine.planner.images.assert_called_once_with(
        "convert",
        "input",
        "output",
        output_format="jpg",
        quality=80,
        resize=None,
    )


@patch("examples.batch_convert_images.WorkflowEngine")
def test_optimize_images_for_web_uses_supported_profile(engine_type):
    engine = _engine()
    engine_type.return_value = engine

    optimize_images_for_web("input", "output", max_width=640, max_height=360, quality=75)

    engine.planner.images.assert_called_once_with(
        "optimize",
        "input",
        "output",
        max_width=640,
        max_height=360,
        quality=75,
    )


@patch("examples.batch_convert_images.WorkflowEngine")
def test_convert_to_webp_batch_uses_supported_profile(engine_type):
    engine = _engine()
    engine_type.return_value = engine

    convert_to_webp_batch("input", "output", quality=70)

    engine.planner.images.assert_called_once_with("webp", "input", "output", quality=70)
