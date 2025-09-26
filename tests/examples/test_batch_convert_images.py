"""
Tests for batch_convert_images example functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from pyffmpegcore.runner import FFmpegRunner
from pyffmpegcore.probe import FFprobeRunner


class TestBatchImageConversion:
    """Test batch image conversion functionality."""

    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    def test_convert_image_basic(self, mock_run):
        """Test basic image conversion."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        from examples.batch_convert_images import convert_image

        result = convert_image("input.png", "output.jpg", quality=85)

        assert result is True
        mock_run.assert_called_once()

    @patch('glob.glob')
    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    @patch('os.makedirs')
    def test_batch_convert_images(self, mock_makedirs, mock_run, mock_glob):
        """Test batch image conversion."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_glob.return_value = ["image1.png", "image2.png"]

        from examples.batch_convert_images import batch_convert_images

        results = batch_convert_images("input_dir/", "output_dir/", ["*.png"], "jpg")

        assert results["total"] == 2
        assert results["successful"] == 2
        assert results["failed"] == 0
        assert mock_run.call_count == 2

    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    @patch('glob.glob')
    @patch('os.makedirs')
    def test_optimize_images_for_web(self, mock_makedirs, mock_glob, mock_run):
        """Test web optimization with resizing."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        # Mock glob to return just one file per pattern
        mock_glob.return_value = ["large_image.jpg"]

        from examples.batch_convert_images import optimize_images_for_web

        results = optimize_images_for_web("input_dir/", "output_dir/")

        # Since glob returns the same list for each pattern, we get 6 files (1 per pattern)
        assert results["total"] == 6
        assert mock_run.called  # Should resize and convert

    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    @patch('glob.glob')
    @patch('os.makedirs')
    def test_convert_to_webp_batch(self, mock_makedirs, mock_glob, mock_run):
        """Test WebP batch conversion."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        # Mock glob to return 2 files total (some patterns might return empty)
        mock_glob.side_effect = [["image1.jpg"], ["image2.png"], [], [], []]  # Different patterns return different results

        from examples.batch_convert_images import convert_to_webp_batch

        results = convert_to_webp_batch("input_dir/", "output_dir/", quality=80, lossless=False)

        assert results["total"] == 2
        # Should call convert_image for each file
        assert mock_run.call_count == 2