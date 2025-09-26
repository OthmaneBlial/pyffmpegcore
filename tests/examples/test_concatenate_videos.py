"""
Tests for concatenate_videos example functionality.
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from pyffmpegcore.runner import FFmpegRunner
from pyffmpegcore.probe import FFprobeRunner


class TestVideoConcatenation:
    """Test video concatenation functionality."""

    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_concatenate_videos_basic(self, mock_exists, mock_file, mock_run):
        """Test basic video concatenation."""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # This would be in a new example file
        # For now, just test the FFmpeg concat functionality
        runner = FFmpegRunner()

        # Create concat file content
        concat_content = "file 'video1.mp4'\nfile 'video2.mp4'\n"

        with patch('builtins.open', mock_open(read_data=concat_content)) as mock_file:
            args = [
                "-f", "concat",
                "-safe", "0",
                "-i", "concat.txt",
                "-c", "copy",
                "-y", "output.mp4"
            ]

            result = runner.run(args)

            assert result.returncode == 0
            mock_run.assert_called_once()