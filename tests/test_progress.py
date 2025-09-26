"""
Tests for ProgressTracker.
"""

import pytest
import subprocess
from unittest.mock import patch, MagicMock, call
from pyffmpegcore.progress import ProgressTracker, ProgressCallback


class TestProgressTracker:
    """Test ProgressTracker functionality."""

    def test_parse_progress_line(self):
        """Test parsing of progress lines."""
        tracker = ProgressTracker(lambda x: None)

        # Test valid progress line
        line = "frame=  123 fps=25.0 q=28.0 size=   12345kB time=00:00:05.00 bitrate=1234.5kbits/s speed=1.25x"
        progress = tracker._parse_progress_line(line)

        assert progress is not None
        assert progress["frame"] == 123
        assert progress["fps"] == 25.0
        assert progress["size_kb"] == 12345.0
        assert progress["time_seconds"] == 5.0
        assert progress["bitrate_kbps"] == 1234.5
        assert progress["speed"] == 1.25

    def test_parse_progress_line_end(self):
        """Test parsing of end progress line."""
        tracker = ProgressTracker(lambda x: None)

        line = "progress=end"
        progress = tracker._parse_progress_line(line)

        assert progress is not None
        assert progress["status"] == "end"

    def test_parse_progress_line_invalid(self):
        """Test parsing of invalid progress line."""
        tracker = ProgressTracker(lambda x: None)

        line = "invalid line"
        progress = tracker._parse_progress_line(line)

        assert progress is None

    def test_time_to_seconds(self):
        """Test time string to seconds conversion."""
        tracker = ProgressTracker(lambda x: None)

        assert tracker._time_to_seconds("00:00:05.00") == 5.0
        assert tracker._time_to_seconds("00:01:30.50") == 90.5
        assert tracker._time_to_seconds("01:00:00.00") == 3600.0
        assert tracker._time_to_seconds("5.5") == 5.5

    @patch('subprocess.Popen')
    @patch('threading.Thread')
    def test_run_with_progress(self, mock_thread, mock_popen):
        """Test run method with progress callback."""
        # Mock process
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("stdout", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Mock thread
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        # Mock stderr pipe
        mock_stderr = MagicMock()
        mock_stderr.readline.side_effect = ["progress line", ""]  # One line then EOF
        mock_process.stderr = mock_stderr

        callback_calls = []
        tracker = ProgressTracker(lambda x: callback_calls.append(x))

        cmd = ["ffmpeg", "-i", "input.mp4", "output.mp4"]
        result = tracker.run(cmd)

        assert result.returncode == 0
        # Check that progress options were added
        call_args = mock_popen.call_args[0][0]
        assert "-progress" in call_args
        assert "pipe:1" in call_args
        assert "-nostats" in call_args


class TestProgressCallback:
    """Test ProgressCallback functionality."""

    def test_callback_without_duration(self):
        """Test callback without total duration."""
        callback = ProgressCallback()

        # Mock print to capture output
        with patch('builtins.print') as mock_print:
            callback({"frame": 100, "fps": 25.0})
            mock_print.assert_called_once_with("Progress: {'frame': 100, 'fps': 25.0}")

    def test_callback_with_duration(self):
        """Test callback with total duration."""
        callback = ProgressCallback(total_duration=120.0)

        with patch('builtins.print') as mock_print:
            callback({"time_seconds": 60.0})
            mock_print.assert_called_once_with("50.0% - {'time_seconds': 60.0}")

    def test_callback_end(self):
        """Test callback with end status."""
        callback = ProgressCallback(total_duration=120.0)

        with patch('builtins.print') as mock_print:
            callback({"status": "end"})
            mock_print.assert_called_once_with("100% - Conversion completed!")

    def test_parse_progress_pipe_time_variants(self):
        """Test parsing different time formats from -progress pipe:1."""
        tracker = ProgressTracker(lambda x: None)

        # Test out_time
        progress = tracker._parse_progress_pipe_line("out_time=00:01:30.500")
        assert progress == {"time_seconds": 90.5}

        # Test out_time_ms
        progress = tracker._parse_progress_pipe_line("out_time_ms=90500")
        assert progress == {"time_seconds": 90.5}

        # Test out_time_us
        progress = tracker._parse_progress_pipe_line("out_time_us=90500000")
        assert progress == {"time_seconds": 90.5}