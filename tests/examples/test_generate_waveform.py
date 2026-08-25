"""Waveform examples delegate to the supported image workflow."""

from unittest.mock import MagicMock, patch

from examples.generate_waveform import generate_detailed_waveform, generate_waveform_image


def _engine():
    engine = MagicMock()
    engine.run.return_value = MagicMock(succeeded=True, items=())
    return engine


@patch("examples.generate_waveform.WorkflowEngine")
def test_generate_waveform_image_uses_shared_plan(engine_type):
    engine = _engine()
    engine_type.return_value = engine

    assert generate_waveform_image("input.mp3", "output.png", width=1000, height=200, colors="red") is True
    engine.planner.waveform.assert_called_once_with(
        "input.mp3",
        "output.png",
        width=1000,
        height=200,
        colors="red",
    )


@patch("examples.generate_waveform.WorkflowEngine")
def test_generate_detailed_waveform_uses_curated_high_contrast_colors(engine_type):
    engine = _engine()
    engine_type.return_value = engine

    assert generate_detailed_waveform("input.mp3", "output.png", width=900, height=240) is True
    engine.planner.waveform.assert_called_once_with(
        "input.mp3",
        "output.png",
        width=900,
        height=240,
        colors="green|red",
    )
