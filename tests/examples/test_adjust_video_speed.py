"""Examples must delegate speed work to the shared public engine."""

from unittest.mock import MagicMock, patch

from examples.adjust_video_speed import adjust_audio_tempo, change_video_speed


def _engine():
    engine = MagicMock()
    engine.run.return_value = MagicMock(succeeded=True, items=())
    return engine


@patch("examples.adjust_video_speed.WorkflowEngine")
def test_change_video_speed_uses_shared_plan(engine_type):
    engine = _engine()
    engine_type.return_value = engine

    assert change_video_speed("input.mp4", "output.mp4", 2.0, maintain_audio_pitch=True) is True
    engine.planner.speed.assert_called_once_with(
        "video",
        "input.mp4",
        "output.mp4",
        factor=2.0,
        preserve_pitch=True,
    )
    engine.run.assert_called_once_with(engine.planner.speed.return_value, progress_callback=None)


@patch("examples.adjust_video_speed.WorkflowEngine")
def test_adjust_audio_tempo_uses_shared_plan(engine_type):
    engine = _engine()
    engine_type.return_value = engine

    assert adjust_audio_tempo("input.mp3", "output.m4a", 1.25, maintain_pitch=False) is True
    engine.planner.speed.assert_called_once_with(
        "audio",
        "input.mp3",
        "output.m4a",
        factor=1.25,
        preserve_pitch=False,
    )
