"""
Tests for FFmpegRunner.
"""

import subprocess

import pytest
from unittest.mock import patch, MagicMock
from pyffmpegcore.runner import FFmpegRunner
from pyffmpegcore.probe import FFprobeRunner


class TestFFmpegRunner:
    """Test FFmpegRunner functionality."""

    def test_init(self):
        """Test FFmpegRunner initialization."""
        runner = FFmpegRunner()
        assert runner.ffmpeg_path == "ffmpeg"

        runner = FFmpegRunner("/custom/path/ffmpeg")
        assert runner.ffmpeg_path == "/custom/path/ffmpeg"

    @patch('subprocess.run')
    def test_run(self, mock_run):
        """Test basic run method."""
        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")

        runner = FFmpegRunner()
        result = runner.run(["-version"])

        mock_run.assert_called_once()
        assert result.returncode == 0

    @patch('subprocess.run')
    def test_convert(self, mock_run):
        """Test convert method."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()
        result = runner.convert("input.mp4", "output.avi", video_codec="libx264")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-i" in args
        assert "input.mp4" in args
        assert "output.avi" in args
        assert "-c:v" in args
        assert "libx264" in args

    @patch('subprocess.run')
    def test_resize(self, mock_run):
        """Test resize method."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()
        result = runner.resize("input.mp4", "output.mp4", 640, 480)

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-vf" in args
        assert "scale=640:480" in args

    @patch('subprocess.run')
    def test_compress(self, mock_run):
        """Test compress method."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()
        result = runner.compress("input.mp4", "output.mp4", crf=28)

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-c:v" in args
        assert "libx264" in args
        assert "-crf" in args
        assert "28" in args

    @patch('subprocess.run')
    def test_get_version(self, mock_run):
        """Test get_version method."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ffmpeg version 4.4\n", stderr="")

        runner = FFmpegRunner()
        version = runner.get_version()

        assert "ffmpeg version 4.4" in version

    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    def test_compress_with_progress_callback(self, mock_run):
        """Test compress method with progress callback."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()
        callback = lambda x: None

        result = runner.compress("input.mp4", "output.mp4", crf=28, progress_callback=callback)

        # Verify run was called with progress_callback as second positional argument
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0]
        assert len(call_args) >= 2  # args list and progress_callback
        assert call_args[1] == callback  # Second argument should be the callback

    @patch('subprocess.run')
    def test_convert_audio_only(self, mock_run):
        """Test convert method with audio_only=True."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()
        result = runner.convert("input.mp4", "output.mp3", audio_only=True, audio_codec="mp3")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-vn" in args  # No video flag
        assert "-c:a" in args
        assert "mp3" in args
        # Should not have video-related options
        assert "-c:v" not in args
        assert "-pix_fmt" not in args

    @patch('subprocess.run')
    def test_convert_with_threads(self, mock_run):
        """Test convert method with threads parameter."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()
        result = runner.convert("input.mp4", "output.mp4", threads=4)

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-threads" in args
        assert "4" in args

    @patch('subprocess.run')
    def test_resize_with_pix_fmt_override(self, mock_run):
        """Test resize method with pix_fmt override."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()
        result = runner.resize("input.mp4", "output.mp4", 640, 480, pix_fmt="rgb24")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-pix_fmt" in args
        assert "rgb24" in args

    @patch('subprocess.run')
    def test_extract_audio_uses_extension_based_default_codec(self, mock_run):
        """Test extract_audio chooses a sensible default codec."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()
        runner.extract_audio("input.mp4", "output.mp3")

        args = mock_run.call_args[0][0]
        assert "-c:a" in args
        assert "libmp3lame" in args

    def test_extract_audio_missing_input_returns_failure(self, tmp_path):
        """Test extract_audio fails cleanly for a missing input file."""
        runner = FFmpegRunner()
        result = runner.extract_audio(str(tmp_path / "missing.mp4"), str(tmp_path / "output.m4a"))

        assert result.returncode != 0
        assert result.stderr

    def test_extract_audio_real_file_contains_audio_only_stream(self, tmp_path):
        """Test extract_audio on a real sample clip."""
        input_file = tmp_path / "input.mp4"
        output_file = tmp_path / "output.m4a"

        create_cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "testsrc=size=160x120:rate=24",
            "-f", "lavfi",
            "-i", "sine=frequency=660:sample_rate=44100",
            "-t", "1.5",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-y", str(input_file),
        ]
        subprocess.run(create_cmd, check=True, capture_output=True, text=True)

        runner = FFmpegRunner()
        result = runner.extract_audio(str(input_file), str(output_file))

        assert result.returncode == 0
        assert output_file.exists()

        metadata = FFprobeRunner().probe(str(output_file))
        assert "audio" in metadata
        assert "video" not in metadata

    @patch('subprocess.run')
    def test_compress_single_pass_bitrate_mode(self, mock_run):
        """Test compress method in bitrate mode."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()
        result = runner.compress("input.mp4", "output.mp4", video_bitrate="1000k")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-b:v" in args
        assert "1000k" in args
        assert "-crf" not in args  # Should not use CRF in bitrate mode

    @patch('pyffmpegcore.probe.FFprobeRunner.probe')
    @patch('subprocess.run')
    def test_compress_two_pass_with_overhead_pct(self, mock_run, mock_probe):
        """Test compress method with custom overhead_pct."""
        # Mock probe to return duration
        mock_probe.return_value = {"duration": 120.0, "audio": {"bit_rate": 128000}}

        # Mock the first pass
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # First pass
            MagicMock(returncode=0, stdout="", stderr="")   # Second pass
        ]

        runner = FFmpegRunner()
        result = runner.compress("input.mp4", "output.mp4", target_size_kb=10240, overhead_pct=2.0)

        # Should have made 2 calls (2 passes)
        assert mock_run.call_count == 2

    @patch('subprocess.run')
    def test_compress_copy_codec_forbidden_two_pass(self, mock_run):
        """Test that video_codec='copy' is forbidden in two-pass compression."""
        runner = FFmpegRunner()

        with pytest.raises(ValueError) as exc_info:
            runner.compress("input.mp4", "output.mp4", target_size_kb=10240, video_codec="copy")

        assert "video_codec='copy' is not supported" in str(exc_info.value)

    @patch('subprocess.run')
    def test_compress_copy_codec_single_pass(self, mock_run):
        """Test compress method with video_codec='copy' in single-pass."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()
        result = runner.compress("input.mp4", "output.mp4", crf=23, video_codec="copy")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-c:v" in args
        assert "copy" in args
        # Should not have encoding parameters when copying
        assert "-crf" not in args
        assert "-preset" not in args
        assert "-pix_fmt" not in args

    @patch('pyffmpegcore.runner.FFmpegRunner._cleanup_pass_logs')
    @patch('pyffmpegcore.runner.FFmpegRunner._parse_bitrate')
    @patch('pyffmpegcore.probe.FFprobeRunner')
    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    def test_compress_two_pass(self, mock_run, mock_ffprobe_class, mock_parse_bitrate, mock_cleanup):
        """Test two-pass compression."""
        # Mock FFprobe
        mock_ffprobe = MagicMock()
        mock_ffprobe.probe.return_value = {"duration": 120.0}
        mock_ffprobe_class.return_value = mock_ffprobe

        # Mock parse_bitrate
        mock_parse_bitrate.return_value = 128 * 1024  # 128kbps

        # Mock subprocess runs (pass 1 and pass 2)
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # Pass 1
            MagicMock(returncode=0, stdout="", stderr="")   # Pass 2
        ]

        runner = FFmpegRunner()
        result = runner.compress("input.mp4", "output.mp4", target_size_kb=10240)

        # Verify two subprocess calls were made
        assert mock_run.call_count == 2

        # Verify cleanup was called
        mock_cleanup.assert_called_once_with("output.mp4")

        # Verify pass 1 had -an (no audio) flag
        pass1_args = mock_run.call_args_list[0][0][0]
        assert "-an" in pass1_args
        assert "os.devnull" in str(pass1_args) or "/dev/null" in str(pass1_args)

    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    def test_convert_with_progress_callback(self, mock_run):
        """Test convert method with progress callback."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()
        callback = lambda x: None

        result = runner.convert("input.mp4", "output.mp4", progress_callback=callback)

        # Verify run was called with progress_callback as second positional argument
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0]
        assert len(call_args) >= 2  # args list and progress_callback
        assert call_args[1] == callback  # Second argument should be the callback
