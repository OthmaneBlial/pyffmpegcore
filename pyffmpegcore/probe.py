"""
FFprobe metadata extraction.
"""

import subprocess
import json
from typing import Dict, Any, Optional


class FFprobeRunner:
    """
    A runner for extracting metadata from media files using FFprobe.
    """

    def __init__(self, ffprobe_path: str = "ffprobe"):
        """
        Initialize the FFprobe runner.

        Args:
            ffprobe_path: Path to the ffprobe executable. Defaults to "ffprobe".
        """
        self.ffprobe_path = ffprobe_path

    def probe(self, input_file: str) -> Dict[str, Any]:
        """
        Extract simplified metadata from a media file.

        Args:
            input_file: Path to the media file

        Returns:
            Simplified metadata dictionary derived from FFprobe JSON
        """
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            "-show_chapters",
            input_file
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"FFprobe failed: {result.stderr}")

        data = json.loads(result.stdout)
        return self._simplify_metadata(data)

    def _simplify_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simplify the raw ffprobe JSON output into a more user-friendly format.

        Args:
            data: Raw ffprobe JSON data

        Returns:
            Simplified metadata dictionary
        """
        metadata = {}

        # Format information
        if "format" in data:
            fmt = data["format"]
            metadata["filename"] = fmt.get("filename")
            metadata["format_name"] = fmt.get("format_name")
            metadata["format_long_name"] = fmt.get("format_long_name")
            metadata["duration"] = float(fmt.get("duration", 0))
            metadata["size"] = int(fmt.get("size", 0))
            metadata["bit_rate"] = int(fmt.get("bit_rate", 0)) if fmt.get("bit_rate") else None

        # Stream information
        if "streams" in data:
            streams = []
            for stream in data["streams"]:
                stream_info = {
                    "index": stream.get("index"),
                    "codec_type": stream.get("codec_type"),
                    "codec_name": stream.get("codec_name"),
                    "codec_long_name": stream.get("codec_long_name"),
                    "profile": stream.get("profile"),
                    "width": stream.get("width"),
                    "height": stream.get("height"),
                    "sample_rate": int(stream.get("sample_rate")) if stream.get("sample_rate") else None,
                    "channels": stream.get("channels"),
                    "bit_rate": int(stream.get("bit_rate")) if stream.get("bit_rate") else None,
                    "duration": float(stream.get("duration", 0)) if stream.get("duration") else None,
                }
                # Remove None values
                stream_info = {k: v for k, v in stream_info.items() if v is not None}
                streams.append(stream_info)

            metadata["streams"] = streams

            # Extract video and audio info for convenience
            video_streams = [s for s in streams if s.get("codec_type") == "video"]
            audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

            if video_streams:
                video = video_streams[0]  # Usually the first video stream
                metadata["video"] = {
                    "codec": video.get("codec_name"),
                    "width": video.get("width"),
                    "height": video.get("height"),
                    "duration": video.get("duration"),
                    "bit_rate": video.get("bit_rate"),
                }

            if audio_streams:
                audio = audio_streams[0]  # Usually the first audio stream
                metadata["audio"] = {
                    "codec": audio.get("codec_name"),
                    "sample_rate": int(audio.get("sample_rate")) if audio.get("sample_rate") else None,
                    "channels": audio.get("channels"),
                    "bit_rate": audio.get("bit_rate"),
                }

        # Chapter information
        if "chapters" in data and data["chapters"]:
            chapters = []
            for chapter in data["chapters"]:
                chapter_info = {
                    "id": chapter.get("id"),
                    "start": float(chapter.get("start_time", 0)),
                    "end": float(chapter.get("end_time", 0)),
                    "title": chapter.get("tags", {}).get("title"),
                }
                chapters.append(chapter_info)
            metadata["chapters"] = chapters

        return metadata

    def get_duration(self, input_file: str) -> float:
        """
        Get the duration of a media file in seconds.

        Args:
            input_file: Path to the media file

        Returns:
            Duration in seconds
        """
        metadata = self.probe(input_file)
        return metadata.get("duration", 0.0)

    def get_resolution(self, input_file: str) -> Optional[tuple]:
        """
        Get the resolution of a video file.

        Args:
            input_file: Path to the video file

        Returns:
            Tuple of (width, height) or None if not a video
        """
        metadata = self.probe(input_file)
        if "video" in metadata:
            video = metadata["video"]
            return (video.get("width"), video.get("height"))
        return None

    def get_bitrate(self, input_file: str) -> Optional[int]:
        """
        Get the bitrate of a media file.

        Args:
            input_file: Path to the media file

        Returns:
            Bitrate in bits per second
        """
        metadata = self.probe(input_file)
        return metadata.get("bit_rate")

    def get_version(self) -> str:
        """
        Get the FFprobe version.

        Returns:
            Version string
        """
        result = subprocess.run([self.ffprobe_path, "-version"],
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.split('\n')[0]
        else:
            raise RuntimeError(f"Failed to get FFprobe version: {result.stderr}")
