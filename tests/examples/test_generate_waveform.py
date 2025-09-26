"""
Tests for generate_waveform example functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from pyffmpegcore.runner import FFmpegRunner
from pyffmpegcore.probe import FFprobeRunner


class TestWaveformGeneration:
    """Test audio waveform generation functionality."""

    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    def test_generate_waveform_image(self, mock_run):
        """Test basic waveform image generation."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()
        result = runner.generate_waveform("input.mp3", "output.png")

        assert result.returncode == 0
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "showwavespic" in " ".join(args)

    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    def test_generate_detailed_waveform(self, mock_run):
        """Test detailed waveform generation."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = FFmpegRunner()
        result = runner.generate_waveform("input.mp3", "output.png", width=1000, colors="red")

        assert result.returncode == 0
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "showwavespic" in " ".join(args)
        assert "colors=red" in " ".join(args)

    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    def test_generate_waveform_animation(self, mock_run):
        """Test animated waveform generation."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        from examples.generate_waveform import generate_waveform_animation

        result = generate_waveform_animation("input.mp3", "output.mp4", duration=10)

        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "showwaves" in " ".join(args)
        assert "-t" in args
        assert "10" in args

    @patch('pyffmpegcore.probe.FFprobeRunner.probe')
    @patch('pyffmpegcore.runner.FFmpegRunner.run')
    @patch('os.makedirs')
    def test_generate_waveform_with_metadata(self, mock_makedirs, mock_run, mock_probe):
        """Test waveform generation with metadata overlay."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_probe.return_value = {
            "duration": 180.5,
            "audio": {"sample_rate": 44100, "channels": 2}
        }

        from examples.generate_waveform import generate_waveform_with_metadata

        generate_waveform_with_metadata("input.mp3", "output_dir/")

        # Should generate waveform and add metadata overlay
        assert mock_run.call_count == 2  # waveform + overlay
        assert mock_probe.called