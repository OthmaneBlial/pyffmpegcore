"""Thumbnail examples compile every item through the shared planner."""

from unittest.mock import MagicMock, patch

from examples.extract_thumbnail import extract_multiple_thumbnails, extract_smart_thumbnails, extract_thumbnail


def _engine():
    engine = MagicMock()
    engine.run.return_value = MagicMock(succeeded=True, items=())
    return engine


@patch("examples.extract_thumbnail.WorkflowEngine")
def test_extract_thumbnail_uses_shared_plan(engine_type):
    engine = _engine()
    engine_type.return_value = engine

    assert extract_thumbnail("input.mp4", "output.jpg", "00:00:30", width=640) is True
    engine.planner.thumbnail.assert_called_once_with(
        "input.mp4",
        "output.jpg",
        timestamp="00:00:30",
        width=640,
        height=None,
    )


@patch("examples.extract_thumbnail.WorkflowEngine")
def test_extract_multiple_thumbnails_builds_one_shared_plan_per_timestamp(engine_type, tmp_path):
    engines = [_engine(), _engine()]
    engine_type.side_effect = engines

    outputs = extract_multiple_thumbnails("input.mp4", str(tmp_path), ["00:00:10", "00:00:30"])

    assert len(outputs) == 2
    assert engine_type.call_count == 2
    assert all(engine.planner.thumbnail.called for engine in engines)


@patch("examples.extract_thumbnail.FFprobeRunner.get_duration", return_value=120.0)
@patch("examples.extract_thumbnail.WorkflowEngine")
def test_extract_smart_thumbnails_uses_probed_even_intervals(engine_type, _duration, tmp_path):
    engines = [_engine(), _engine(), _engine()]
    engine_type.side_effect = engines

    outputs = extract_smart_thumbnails("input.mp4", str(tmp_path), count=3)

    assert len(outputs) == 3
    planned_timestamps = [engine.planner.thumbnail.call_args.kwargs["timestamp"] for engine in engines]
    assert planned_timestamps == ["30.000", "60.000", "90.000"]
