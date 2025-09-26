"""
Tests for mix_audio example functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from pyffmpegcore.runner import FFmpegRunner
from pyffmpegcore.probe import FFprobeRunner


class TestAudioProcessing:
    """Test advanced audio processing functionality."""

    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    def test_audio_normalization(self, mock_run):
        """Test audio normalization."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()

        # Audio normalization using loudnorm filter
        args = [
            "-i", "input.wav",
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", "44100",
            "-y", "normalized.wav"
        ]

        result = runner.run(args)

        assert result.returncode == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "loudnorm" in " ".join(call_args)

    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    def test_video_speed_adjustment(self, mock_run):
        """Test video speed adjustment."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()

        # Speed up video by 2x
        args = [
            "-i", "input.mp4",
            "-filter_complex", "[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-y", "sped_up.mp4"
        ]

        result = runner.run(args)

        assert result.returncode == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "setpts" in " ".join(call_args)
        assert "atempo" in " ".join(call_args)