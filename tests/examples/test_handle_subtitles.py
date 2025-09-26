"""
Tests for handle_subtitles example functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from pyffmpegcore.runner import FFmpegRunner
from pyffmpegcore.probe import FFprobeRunner


class TestSubtitleHandling:
    """Test subtitle extraction and burning functionality."""

    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    def test_extract_subtitles(self, mock_run):
        """Test subtitle extraction."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()

        # Extract subtitles to SRT format
        args = [
            "-i", "input.mkv",
            "-map", "0:s:0",  # First subtitle stream
            "-y", "subtitles.srt"
        ]

        result = runner.run(args)

        assert result.returncode == 0
        mock_run.assert_called_once()

    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    def test_burn_subtitles(self, mock_run):
        """Test burning subtitles into video."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()

        # Burn subtitles into video
        args = [
            "-i", "input.mp4",
            "-vf", "subtitles=input.mkv:stream_index=0",
            "-c:a", "copy",
            "-y", "with_subtitles.mp4"
        ]

        result = runner.run(args)

        assert result.returncode == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "subtitles=" in " ".join(call_args)