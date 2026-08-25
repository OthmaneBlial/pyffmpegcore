"""Concatenation examples use shared copy and re-encode plans."""

from unittest.mock import MagicMock, patch

from examples.concatenate_videos import concatenate_videos_basic, concatenate_videos_reencode


def _engine():
    engine = MagicMock()
    engine.run.return_value = MagicMock(succeeded=True, items=())
    return engine


@patch("examples.concatenate_videos.WorkflowEngine")
def test_concatenate_videos_basic_uses_shared_copy_plan(engine_type):
    engine = _engine()
    engine_type.return_value = engine

    assert concatenate_videos_basic(["one.mp4", "two.mp4"], "joined.mp4") is True
    engine.planner.concat.assert_called_once_with(["one.mp4", "two.mp4"], "joined.mp4", mode="copy")


@patch("examples.concatenate_videos.WorkflowEngine")
def test_concatenate_videos_reencode_uses_shared_codec_plan(engine_type):
    engine = _engine()
    engine_type.return_value = engine

    assert concatenate_videos_reencode(["one.mp4", "two.webm"], "joined.mp4") is True
    engine.planner.concat.assert_called_once_with(
        ["one.mp4", "two.webm"],
        "joined.mp4",
        mode="reencode",
        video_codec="libx264",
        audio_codec="aac",
    )
