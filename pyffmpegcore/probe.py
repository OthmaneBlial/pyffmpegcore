"""
FFprobe metadata extraction.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from .domain import MediaInfo, StreamInfo


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

    def probe(self, input_file: str, *, raw: bool = False) -> dict[str, Any]:
        """
        Extract simplified metadata from a media file.

        Args:
            input_file: Path to the media file

        Returns:
            Simplified metadata dictionary derived from FFprobe JSON
        """
        data = self.probe_raw(input_file)
        return data if raw else self._simplify_metadata(data)

    def probe_raw(self, input_file: str) -> dict[str, Any]:
        """Return the complete FFprobe JSON document without dropping fields."""
        cmd = [
            self.ffprobe_path,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            "-show_chapters",
            input_file,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"FFprobe executable '{self.ffprobe_path}' was not found. Install FFmpeg or pass a valid ffprobe_path."
            ) from exc

        if result.returncode != 0:
            stderr = result.stderr.strip() or f"Unable to probe '{input_file}'"
            raise RuntimeError(f"FFprobe failed for '{input_file}': {stderr}")

        data = json.loads(result.stdout)
        if not isinstance(data, dict):
            raise RuntimeError(f"FFprobe returned an invalid JSON document for '{input_file}'")
        return data

    def probe_media(self, input_file: str) -> MediaInfo:
        """Return typed metadata while retaining decision-relevant stream details."""
        simplified = self.probe(input_file)
        streams = tuple(
            StreamInfo(
                index=int(stream.get("index", 0)),
                codec_type=str(stream.get("codec_type", "unknown")),
                codec_name=stream.get("codec_name"),
                profile=stream.get("profile"),
                width=stream.get("width"),
                height=stream.get("height"),
                sample_rate=stream.get("sample_rate"),
                channels=stream.get("channels"),
                bit_rate=stream.get("bit_rate"),
                duration=stream.get("duration"),
                language=stream.get("language"),
                rotation=stream.get("rotation"),
                tags=stream.get("tags", {}),
                disposition=stream.get("disposition", {}),
                color=stream.get("color", {}),
                side_data=tuple(stream.get("side_data_list", [])),
                details=stream.get("details", {}),
            )
            for stream in simplified.get("streams", [])
        )
        return MediaInfo(
            path=simplified.get("filename") or input_file,
            format_name=simplified.get("format_name"),
            format_long_name=simplified.get("format_long_name"),
            duration=simplified.get("duration"),
            size=simplified.get("size"),
            bit_rate=simplified.get("bit_rate"),
            tags=simplified.get("tags", {}),
            streams=streams,
            chapters=tuple(simplified.get("chapters", [])),
        )

    def _simplify_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Simplify the raw ffprobe JSON output into a more user-friendly format.

        Args:
            data: Raw ffprobe JSON data

        Returns:
            Simplified metadata dictionary
        """
        metadata: dict[str, Any] = {}

        # Format information
        if "format" in data:
            fmt = data["format"]
            metadata["filename"] = fmt.get("filename")
            metadata["format_name"] = fmt.get("format_name")
            metadata["format_long_name"] = fmt.get("format_long_name")
            metadata["duration"] = float(fmt.get("duration", 0))
            metadata["size"] = int(fmt.get("size", 0))
            metadata["bit_rate"] = int(fmt.get("bit_rate", 0)) if fmt.get("bit_rate") else None
            metadata["tags"] = dict(fmt.get("tags", {}))

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
                    "tags": dict(stream.get("tags", {})),
                    "disposition": dict(stream.get("disposition", {})),
                    "side_data_list": list(stream.get("side_data_list", [])),
                }
                color = {
                    name: stream[name]
                    for name in ("color_range", "color_space", "color_transfer", "color_primaries")
                    if stream.get(name) is not None
                }
                if color:
                    stream_info["color"] = color
                language = stream.get("tags", {}).get("language")
                if language:
                    stream_info["language"] = language
                rotation = stream.get("tags", {}).get("rotate")
                if rotation is None:
                    rotation = next(
                        (
                            item.get("rotation")
                            for item in stream.get("side_data_list", [])
                            if item.get("rotation") is not None
                        ),
                        None,
                    )
                if rotation is not None:
                    stream_info["rotation"] = float(rotation)
                preserved_details = {
                    name: stream[name]
                    for name in (
                        "codec_tag_string",
                        "codec_tag",
                        "codec_time_base",
                        "time_base",
                        "start_time",
                        "avg_frame_rate",
                        "r_frame_rate",
                        "field_order",
                        "extradata_size",
                    )
                    if stream.get(name) is not None
                }
                if preserved_details:
                    stream_info["details"] = preserved_details
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
                sample_rate = audio.get("sample_rate")
                metadata["audio"] = {
                    "codec": audio.get("codec_name"),
                    "sample_rate": int(sample_rate) if sample_rate is not None else None,
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
                    "tags": dict(chapter.get("tags", {})),
                    "time_base": chapter.get("time_base"),
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

    def get_resolution(self, input_file: str) -> tuple | None:
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

    def get_bitrate(self, input_file: str) -> int | None:
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
        result = subprocess.run([self.ffprobe_path, "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.split("\n")[0]
        raise RuntimeError(f"Failed to get FFprobe version: {result.stderr}")
