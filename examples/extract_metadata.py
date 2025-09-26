#!/usr/bin/env python3
"""
Example: Extract metadata from a video file.
"""

from pyffmpegcore import FFprobeRunner

def main():
    # Initialize FFprobe runner
    ffprobe = FFprobeRunner()

    # Extract metadata
    metadata = ffprobe.probe("sample.mp4")

    print("File Metadata:")
    print(f"Filename: {metadata.get('filename')}")
    print(f"Format: {metadata.get('format_long_name')}")
    print(f"Duration: {metadata.get('duration', 0):.2f} seconds")
    print(f"Size: {metadata.get('size', 0)} bytes")
    print(f"Bitrate: {metadata.get('bit_rate')} bps")

    if "video" in metadata:
        video = metadata["video"]
        print("\nVideo Stream:")
        print(f"Codec: {video.get('codec')}")
        print(f"Resolution: {video.get('width')}x{video.get('height')}")
        print(f"Duration: {video.get('duration', 0):.2f} seconds")

    if "audio" in metadata:
        audio = metadata["audio"]
        print("\nAudio Stream:")
        print(f"Codec: {audio.get('codec')}")
        print(f"Sample Rate: {audio.get('sample_rate')} Hz")
        print(f"Channels: {audio.get('channels')}")

    # Quick access methods
    duration = ffprobe.get_duration("sample.mp4")
    resolution = ffprobe.get_resolution("sample.mp4")
    bitrate = ffprobe.get_bitrate("sample.mp4")

    print("\nQuick Access:")
    print(f"Duration: {duration:.2f}s")
    print(f"Resolution: {resolution}")
    print(f"Bitrate: {bitrate} bps")

if __name__ == "__main__":
    main()