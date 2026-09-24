"""
Tests for ProgressTracker.
"""

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from pyffmpegcore.progress import ProgressCallback, ProgressTracker


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

    @pytest.mark.parametrize("use_pipe", [True, False])
    @patch("subprocess.Popen")
    def test_run_with_progress_drains_each_pipe_once(self, mock_popen, use_pipe):
        """Progress readers and communicate must not compete for the same pipe."""
        mock_process = MagicMock()
        mock_process.communicate.side_effect = AssertionError("communicate would race the progress reader")
        mock_process.returncode = 0
        mock_process.wait.return_value = 0
        if use_pipe:
            mock_process.stdout = StringIO("frame=bad\nframe=123\nprogress=end\n")
            mock_process.stderr = StringIO("diagnostic")
        else:
            mock_process.stdout = StringIO("captured stdout")
            mock_process.stderr = StringIO(
                "frame=  123 fps=25.0 q=28.0 size=   12345kB time=00:00:05.00 "
                "bitrate=1234.5kbits/s speed=1.25x\nprogress=end\n"
            )
        mock_popen.return_value = mock_process

        callback_calls = []
        tracker = ProgressTracker(lambda x: callback_calls.append(x), use_pipe=use_pipe)

        cmd = ["ffmpeg", "-i", "input.mp4", "output.mp4"]
        result = tracker.run(cmd)

        assert result.returncode == 0
        assert callback_calls[-1]["status"] == "end"
        assert callback_calls[0]["frame"] == 123
        mock_process.communicate.assert_not_called()
        mock_process.wait.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        if use_pipe:
            assert "-progress" in call_args
            assert "pipe:1" in call_args
            assert "-nostats" in call_args
            assert result.stderr == "diagnostic"
        else:
            assert "-progress" not in call_args
            assert result.stdout == "captured stdout"
        assert mock_popen.call_args.kwargs["encoding"] == "utf-8"
        assert mock_popen.call_args.kwargs["errors"] == "replace"

    def test_run_resets_progress_between_processes(self):
        process = MagicMock()
        process.stdout = StringIO("progress=end\n")
        process.stderr = StringIO("")
        process.returncode = 0
        process.wait.return_value = 0
        callback_calls = []
        tracker = ProgressTracker(callback_calls.append)
        tracker.progress.update({"frame": 12, "status": "end"})

        with patch("subprocess.Popen", return_value=process):
            tracker.run(["ffmpeg"])

        assert callback_calls == [{"status": "end"}]

    def test_callback_error_is_raised_after_process_pipes_are_drained(self):
        process = MagicMock()
        process.stdout = StringIO("frame=12\nprogress=end\n")
        process.stderr = StringIO("")
        process.returncode = 0
        process.wait.return_value = 0

        def broken_callback(_progress):
            raise RuntimeError("callback failed")

        with patch("subprocess.Popen", return_value=process):
            with pytest.raises(RuntimeError, match="callback failed"):
                ProgressTracker(broken_callback).run(["ffmpeg"])

        process.wait.assert_called_once()


class TestProgressCallback:
    """Test ProgressCallback functionality."""

    def test_callback_without_duration(self):
        """Test callback without total duration."""
        callback = ProgressCallback()

        # Mock print to capture output
        with patch("builtins.print") as mock_print:
            callback({"frame": 100, "fps": 25.0})
            mock_print.assert_called_once_with("Progress: {'frame': 100, 'fps': 25.0}")

    def test_callback_with_duration(self):
        """Test callback with total duration."""
        callback = ProgressCallback(total_duration=120.0)

        with patch("builtins.print") as mock_print:
            callback({"time_seconds": 60.0})
            mock_print.assert_called_once_with("50.0% - {'time_seconds': 60.0}")

    def test_callback_end(self):
        """Test callback with end status."""
        callback = ProgressCallback(total_duration=120.0)

        with patch("builtins.print") as mock_print:
            callback({"status": "end"})
            mock_print.assert_called_once_with("100% - Conversion completed!")

    def test_parse_progress_pipe_time_variants(self):
        """Test parsing different time formats from -progress pipe:1."""
        tracker = ProgressTracker(lambda x: None)

        # Test out_time
        progress = tracker._parse_progress_pipe_line("out_time=00:01:30.500")
        assert progress == {"time_seconds": 90.5, "status": "progress"}

        # Test out_time_ms
        progress = tracker._parse_progress_pipe_line("out_time_ms=90500000")
        assert progress == {"time_seconds": 90.5, "status": "progress"}

        # Test out_time_us
        progress = tracker._parse_progress_pipe_line("out_time_us=90500000")
        assert progress == {"time_seconds": 90.5, "status": "progress"}
