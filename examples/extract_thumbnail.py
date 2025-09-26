#!/usr/bin/env python3
"""
Example: Extract thumbnails from video files for quick previews.

This example demonstrates how to extract single frames or thumbnails from video
files at specific timestamps, which is useful for:
- Video preview generation
- Content management systems
- Social media thumbnails
- Video editing workflows
"""

from pyffmpegcore import FFmpegRunner, FFprobeRunner
import os

def extract_thumbnail(video_path: str, output_path: str, timestamp: str = "00:00:01",
                     width: int = 320, height: int = None, quality: int = 2):
    """
    Extract a thumbnail from a video at a specific timestamp.

    Args:
        video_path: Path to input video file
        output_path: Path to save the thumbnail (e.g., 'thumbnail.jpg')
        timestamp: Time position in HH:MM:SS format (default: 1 second in)
        width: Thumbnail width in pixels
        height: Thumbnail height in pixels (maintains aspect ratio if None)
        quality: JPEG quality (1-31, lower = higher quality)
    """
    ffmpeg = FFmpegRunner()

    # Build filter for scaling and thumbnail extraction
    vf_filters = []

    # Scale to desired size
    if height:
        vf_filters.append(f"scale={width}:{height}")
    else:
        vf_filters.append(f"scale={width}:-1")  # Maintain aspect ratio

    # Seek to timestamp and extract single frame
    args = [
        "-i", video_path,
        "-ss", timestamp,  # Seek to timestamp
        "-vframes", "1",   # Extract 1 frame
        "-vf", ",".join(vf_filters),
        "-q:v", str(quality),  # Quality setting
        "-y", output_path
    ]

    result = ffmpeg.run(args)

    if result.returncode == 0:
        print(f"Thumbnail extracted: {output_path}")
        return True
    else:
        print(f"Failed to extract thumbnail: {result.stderr}")
        return False

def extract_multiple_thumbnails(video_path: str, output_dir: str, timestamps: list,
                               width: int = 320):
    """
    Extract multiple thumbnails from different timestamps in a video.

    Args:
        video_path: Path to input video file
        output_dir: Directory to save thumbnails
        timestamps: List of timestamps in HH:MM:SS format
        width: Thumbnail width in pixels
    """
    os.makedirs(output_dir, exist_ok=True)

    for i, timestamp in enumerate(timestamps):
        output_path = os.path.join(output_dir, f"{i+1:02d}.jpg")
        success = extract_thumbnail(video_path, output_path, timestamp, width)
        if success:
            print(f"Extracted thumbnail {i+1}/{len(timestamps)} at {timestamp}")
        else:
            print(f"Failed to extract thumbnail at {timestamp}")

def extract_smart_thumbnails(video_path: str, output_dir: str, count: int = 5, width: int = 320):
    """
    Extract thumbnails at smart intervals throughout the video.

    Args:
        video_path: Path to input video file
        output_dir: Directory to save thumbnails
        count: Number of thumbnails to extract
        width: Thumbnail width in pixels
    """
    # Get video duration
    ffprobe = FFprobeRunner()
    metadata = ffprobe.probe(video_path)
    duration = metadata.get("duration", 0)

    if duration == 0:
        print("Could not determine video duration")
        return

    # Calculate timestamps at even intervals
    interval = duration / (count + 1)  # Avoid very beginning/end
    timestamps = []

    for i in range(count):
        time_sec = (i + 1) * interval
        hours = int(time_sec // 3600)
        minutes = int((time_sec % 3600) // 60)
        seconds = int(time_sec % 60)
        timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        timestamps.append(timestamp)

    print(f"Extracting {count} thumbnails at {duration:.1f}s intervals")
    extract_multiple_thumbnails(video_path, output_dir, timestamps, width)

def main():
    """Demonstrate thumbnail extraction capabilities."""

    # Example 1: Extract single thumbnail at 30 seconds
    print("=== Extracting single thumbnail ===")
    extract_thumbnail("sample.mp4", "thumbnail_30s.jpg", "00:00:30", width=640)

    # Example 2: Extract multiple thumbnails at specific times
    print("\n=== Extracting multiple thumbnails ===")
    timestamps = ["00:00:10", "00:00:30", "00:01:00", "00:02:00"]
    extract_multiple_thumbnails("sample.mp4", "thumbnails/", timestamps, width=480)

    # Example 3: Extract smart thumbnails at even intervals
    print("\n=== Extracting smart thumbnails ===")
    extract_smart_thumbnails("sample.mp4", "smart_thumbnails/", count=6, width=320)

    print("\nThumbnail extraction examples completed!")

if __name__ == "__main__":
    main()