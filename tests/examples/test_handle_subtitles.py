"""Subtitle examples delegate all command construction to shared plans."""

from unittest.mock import MagicMock, patch

from examples.handle_subtitles import add_subtitle_track, burn_subtitles, extract_subtitles


def _engine():
    engine = MagicMock()
    engine.run.return_value = MagicMock(succeeded=True, items=())
    return engine


@patch("examples.handle_subtitles.WorkflowEngine")
def test_extract_subtitles_uses_shared_plan(engine_type):
    engine = _engine()
    engine_type.return_value = engine

    assert extract_subtitles("input.mkv", "captions.srt", stream_index=1) is True
    engine.planner.subtitles.assert_called_once_with(
        "extract",
        "input.mkv",
        "captions.srt",
        stream_index=1,
    )


@patch("examples.handle_subtitles.WorkflowEngine")
def test_burn_subtitles_uses_shared_plan(engine_type):
    engine = _engine()
    engine_type.return_value = engine

    assert burn_subtitles("input.mp4", "captions.srt", "burned.mp4") is True
    engine.planner.subtitles.assert_called_once_with(
        "burn",
        "input.mp4",
        "burned.mp4",
        subtitle_file="captions.srt",
        font_size=24,
        font_color="&HFFFFFF",
    )


@patch("examples.handle_subtitles.WorkflowEngine")
def test_add_subtitle_track_uses_shared_plan(engine_type):
    engine = _engine()
    engine_type.return_value = engine

    assert add_subtitle_track("input.mp4", "captions.srt", "subtitled.mp4", language="fra") is True
    engine.planner.subtitles.assert_called_once_with(
        "add",
        "input.mp4",
        "subtitled.mp4",
        subtitle_file="captions.srt",
        language="fra",
    )
