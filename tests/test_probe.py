"""
Tests for FFprobeRunner.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from pyffmpegcore.probe import FFprobeRunner


class TestFFprobeRunner:
    """Test FFprobeRunner functionality."""

    def test_init(self):
        """Test FFprobeRunner initialization."""
        runner = FFprobeRunner()
        assert runner.ffprobe_path == "ffprobe"

        runner = FFprobeRunner("/custom/path/ffprobe")
        assert runner.ffprobe_path == "/custom/path/ffprobe"

    @patch("subprocess.run")
    def test_probe(self, mock_run):
        """Test probe method with mock data."""
        mock_data = {
            "format": {
                "filename": "test.mp4",
                "format_name": "mp4",
                "duration": "120.5",
                "size": "15728640",
                "bit_rate": "1048576",
            },
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "bit_rate": "1000000",
                    "duration": "120.5",
                },
                {
                    "index": 1,
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "44100",
                    "channels": 2,
                    "bit_rate": "128000",
                },
            ],
        }

        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_data), stderr="")

        runner = FFprobeRunner()
        result = runner.probe("test.mp4")

        assert result["filename"] == "test.mp4"
        assert result["duration"] == 120.5
        assert result["video"]["codec"] == "h264"
        assert result["video"]["width"] == 1920
        assert result["audio"]["codec"] == "aac"
        assert result["audio"]["sample_rate"] == 44100  # Now int instead of string

    @patch("subprocess.run")
    def test_raw_and_typed_probe_preserve_decision_metadata(self, mock_run):
        mock_data = {
            "format": {"filename": "movie.mkv", "format_name": "matroska", "tags": {"title": "Résumé"}},
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "hevc",
                    "width": 1920,
                    "height": 1080,
                    "color_transfer": "smpte2084",
                    "color_primaries": "bt2020",
                    "tags": {"language": "fra", "rotate": "90"},
                    "disposition": {"default": 1, "attached_pic": 0},
                    "side_data_list": [{"side_data_type": "Display Matrix", "rotation": 90}],
                },
                {"index": 1, "codec_type": "attachment", "codec_name": "ttf", "tags": {"filename": "font.ttf"}},
            ],
            "chapters": [{"id": 0, "start_time": "0", "end_time": "5", "tags": {"title": "Intro"}}],
        }
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_data), stderr="")
        runner = FFprobeRunner()

        assert runner.probe("movie.mkv", raw=True) == mock_data
        typed = runner.probe_media("movie.mkv")

        assert typed.tags == {"title": "Résumé"}
        assert typed.streams[0].language == "fra"
        assert typed.streams[0].rotation == 90.0
        assert typed.streams[0].color["color_transfer"] == "smpte2084"
        assert typed.streams[1].codec_type == "attachment"
        assert typed.chapters[0]["tags"]["title"] == "Intro"

    @patch("subprocess.run")
    def test_get_duration(self, mock_run):
        """Test get_duration method."""
        mock_data = {"format": {"duration": "60.0"}}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_data), stderr="")

        runner = FFprobeRunner()
        duration = runner.get_duration("test.mp4")

        assert duration == 60.0

    @patch("subprocess.run")
    def test_get_resolution(self, mock_run):
        """Test get_resolution method."""
        mock_data = {"streams": [{"codec_type": "video", "width": 1280, "height": 720}]}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_data), stderr="")

        runner = FFprobeRunner()
        resolution = runner.get_resolution("test.mp4")

        assert resolution == (1280, 720)

    @patch("subprocess.run")
    def test_get_resolution_no_video(self, mock_run):
        """Test get_resolution with no video stream."""
        mock_data = {"streams": [{"codec_type": "audio"}]}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_data), stderr="")

        runner = FFprobeRunner()
        resolution = runner.get_resolution("test.mp3")

        assert resolution is None

    @patch("subprocess.run")
    def test_get_bitrate(self, mock_run):
        """Test get_bitrate method."""
        mock_data = {"format": {"bit_rate": "1500000"}}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_data), stderr="")

        runner = FFprobeRunner()
        bitrate = runner.get_bitrate("test.mp4")

        assert bitrate == 1500000

    @patch("subprocess.run")
    def test_get_version(self, mock_run):
        """Test get_version method."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ffprobe version 4.4\n", stderr="")

        runner = FFprobeRunner()
        version = runner.get_version()

        assert "ffprobe version 4.4" in version

    @patch("subprocess.run", side_effect=FileNotFoundError("missing"))
    def test_probe_missing_binary_error(self, mock_run):
        """Test probe raises a readable error when FFprobe is missing."""
        runner = FFprobeRunner("/missing/ffprobe")

        with pytest.raises(RuntimeError) as exc_info:
            runner.probe("test.mp4")

        assert "FFprobe executable '/missing/ffprobe' was not found" in str(exc_info.value)
