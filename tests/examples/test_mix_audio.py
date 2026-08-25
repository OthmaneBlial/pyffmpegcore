"""Audio examples use the same curated workflow actions as the CLI."""

from unittest.mock import MagicMock, patch

from examples.mix_audio import add_background_music, create_audio_mashup, merge_audio_sequentially, mix_audio_files


def _engine():
    engine = MagicMock()
    engine.run.return_value = MagicMock(succeeded=True, items=())
    return engine


@patch("examples.mix_audio.WorkflowEngine")
def test_mix_and_concat_delegate_to_shared_planner(engine_type):
    first, second = _engine(), _engine()
    engine_type.side_effect = [first, second]

    assert mix_audio_files(["voice.wav", "music.mp3"], "mix.mp3", volumes=[1.0, 0.2]) is True
    assert merge_audio_sequentially(["one.mp3", "two.mp3"], "joined.mp3") is True
    first.planner.mix_audio.assert_called_once_with(
        "mix",
        ["voice.wav", "music.mp3"],
        "mix.mp3",
        volumes=[1.0, 0.2],
    )
    second.planner.mix_audio.assert_called_once_with("concat", ["one.mp3", "two.mp3"], "joined.mp3")


@patch("examples.mix_audio.WorkflowEngine")
def test_mashup_and_background_delegate_to_shared_planner(engine_type):
    first, second = _engine(), _engine()
    engine_type.side_effect = [first, second]

    assert create_audio_mashup(["one.mp3", "two.mp3"], "mashup.mp3", crossfade_duration=1.5) is True
    assert add_background_music("voice.wav", "music.mp3", "episode.mp3", bg_volume=0.25) is True
    first.planner.mix_audio.assert_called_once_with(
        "mashup",
        ["one.mp3", "two.mp3"],
        "mashup.mp3",
        crossfade_duration=1.5,
    )
    second.planner.mix_audio.assert_called_once_with(
        "background",
        ["voice.wav", "music.mp3"],
        "episode.mp3",
        background_volume=0.25,
    )
