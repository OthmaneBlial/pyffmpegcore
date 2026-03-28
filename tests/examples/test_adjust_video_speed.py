"""
Tests for the adjust_video_speed example module.
"""

from unittest.mock import MagicMock, patch


class TestAdjustVideoSpeedExample:
    @patch("examples.adjust_video_speed.FFprobeRunner.probe")
    @patch("examples.adjust_video_speed.FFmpegRunner.run")
    def test_change_video_speed_with_audio(self, mock_run, mock_probe):
        mock_probe.return_value = {"audio": {"sample_rate": 48000}}
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        from examples.adjust_video_speed import change_video_speed

        assert change_video_speed("input.mp4", "output.mp4", 2.0, maintain_audio_pitch=True) is True
        args = mock_run.call_args[0][0]
        assert "-filter_complex" in args
        assert "setpts=(PTS-STARTPTS)/2.0" in " ".join(args)
        assert "atempo=2.0" in " ".join(args)

    @patch("examples.adjust_video_speed.FFprobeRunner.probe")
    @patch("examples.adjust_video_speed.FFmpegRunner.run")
    def test_adjust_audio_tempo_without_pitch(self, mock_run, mock_probe):
        mock_probe.return_value = {"audio": {"sample_rate": 44100}}
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        from examples.adjust_video_speed import adjust_audio_tempo

        assert adjust_audio_tempo("input.mp3", "output.m4a", 1.25, maintain_pitch=False) is True
        args = mock_run.call_args[0][0]
        assert "-filter:a" in args
        assert "asetrate=44100*1.25,aresample=44100" in " ".join(args)

    @patch("examples.adjust_video_speed.FFprobeRunner.probe")
    @patch("examples.adjust_video_speed.FFmpegRunner.run")
    def test_create_video_summary_builds_concat_filter(self, mock_run, mock_probe):
        mock_probe.return_value = {
            "duration": 40.0,
            "audio": {"sample_rate": 48000},
        }
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        from examples.adjust_video_speed import create_video_summary

        assert create_video_summary("input.mp4", "summary.mp4", segment_duration=4.0, speed_multiplier=2.0) is True
        args = mock_run.call_args[0][0]
        assert "-filter_complex" in args
        assert "concat=n=" in " ".join(args)
