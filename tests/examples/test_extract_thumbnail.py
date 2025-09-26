"""
Tests for extract_thumbnail example functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from pyffmpegcore.runner import FFmpegRunner
from pyffmpegcore.probe import FFprobeRunner


class TestThumbnailExtraction:
    """Test thumbnail extraction functionality."""

    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    def test_extract_thumbnail_basic(self, mock_run):
        """Test basic thumbnail extraction."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()
        result = runner.extract_thumbnail("input.mp4", "output.jpg", "00:00:30")

        assert result.returncode == 0
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-i" in args
        assert "input.mp4" in args
        assert "-ss" in args
        assert "00:00:30" in args
        assert "-vframes" in args
        assert "1" in args

    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    @patch('os.makedirs')
    def test_extract_multiple_thumbnails(self, mock_makedirs, mock_run):
        """Test multiple thumbnail extraction."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        from examples.extract_thumbnail import extract_multiple_thumbnails

        timestamps = ["00:00:10", "00:00:30"]
        extract_multiple_thumbnails("input.mp4", "output_dir/", timestamps)

        # Should be called twice (once per timestamp)
        assert mock_run.call_count == 2
        assert mock_makedirs.called

    @patch('pyffmpegcore.probe.FFprobeRunner.probe')
    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    @patch('os.makedirs')
    def test_extract_smart_thumbnails(self, mock_makedirs, mock_run, mock_probe):
        """Test smart thumbnail extraction."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_probe.return_value = {"duration": 120.0}  # 2 minutes

        from examples.extract_thumbnail import extract_smart_thumbnails

        extract_smart_thumbnails("input.mp4", "output_dir/", count=3)

        # Should extract 3 thumbnails at 40s, 80s, 120s intervals
        assert mock_run.call_count == 3
        assert mock_probe.called