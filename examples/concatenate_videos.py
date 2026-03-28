#!/usr/bin/env python3
"""
Example: Concatenate multiple video files.

This example demonstrates how to join multiple video files together,
which is useful for:
- Combining video clips into a single movie
- Merging recorded segments
- Creating compilation videos
- Batch processing workflows
"""

import os
import tempfile

from pyffmpegcore import FFmpegRunner
from pyffmpegcore.runner import escape_path_for_concat

def create_concat_file(video_files: list, concat_file: str):
    """
    Create a concat file for FFmpeg.

    Args:
        video_files: List of video file paths
        concat_file: Path to the concat file to create
    """
    with open(concat_file, "w", encoding="utf-8") as f:
        for video_file in video_files:
            f.write(f"file {escape_path_for_concat(video_file)}\n")

def concatenate_videos_basic(video_files: list, output_file: str) -> bool:
    """
    Concatenate videos using basic concat demuxer.

    Args:
        video_files: List of video file paths to concatenate
        output_file: Path for the output concatenated video

    Returns:
        True if successful, False otherwise
    """
    if len(video_files) < 2:
        print("Need at least 2 video files to concatenate")
        return False

    # Create temporary concat file
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
    ) as f:
        concat_file = f.name

    create_concat_file(video_files, concat_file)

    try:
        runner = FFmpegRunner()

        # Use concat demuxer
        args = [
            "-f", "concat",
            "-safe", "0",  # Allow absolute paths
            "-i", concat_file,
            "-c", "copy",  # Copy streams without re-encoding (fastest)
            "-y", output_file
        ]

        result = runner.run(args)

        if result.returncode == 0:
            print(f"Videos concatenated successfully: {output_file}")
            return True
        else:
            print(f"Failed to concatenate videos: {result.stderr}")
            return False

    finally:
        # Clean up temporary file
        try:
            os.unlink(concat_file)
        except OSError:
            pass

def concatenate_videos_reencode(video_files: list, output_file: str,
                               video_codec: str = "libx264", audio_codec: str = "aac") -> bool:
    """
    Concatenate videos with re-encoding (handles different codecs/formats).

    Args:
        video_files: List of video file paths to concatenate
        output_file: Path for the output concatenated video
        video_codec: Video codec to use for output
        audio_codec: Audio codec to use for output

    Returns:
        True if successful, False otherwise
    """
    if len(video_files) < 2:
        print("Need at least 2 video files to concatenate")
        return False

    runner = FFmpegRunner()

    # Build input arguments
    args = []
    for i, video_file in enumerate(video_files):
        args.extend(["-i", video_file])

    # Build filter complex for concatenation
    video_filters = []
    audio_filters = []

    for i in range(len(video_files)):
        video_filters.append(f"[{i}:v]")
        audio_filters.append(f"[{i}:a]")

    video_concat = "".join(video_filters) + f"concat=n={len(video_files)}:v=1:a=0[vout]"
    audio_concat = "".join(audio_filters) + f"concat=n={len(video_files)}:v=0:a=1[aout]"

    args.extend([
        "-filter_complex", f"{video_concat};{audio_concat}",
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", video_codec,
        "-c:a", audio_codec,
        "-y", output_file
    ])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Videos concatenated with re-encoding: {output_file}")
        return True
    else:
        print(f"Failed to concatenate videos: {result.stderr}")
        return False

def concatenate_videos_with_transitions(video_files: list, output_file: str,
                                       transition_duration: float = 1.0) -> bool:
    """
    Concatenate videos with crossfade transitions between clips.

    Args:
        video_files: List of video file paths to concatenate
        output_file: Path for the output video with transitions
        transition_duration: Duration of crossfade in seconds

    Returns:
        True if successful, False otherwise
    """
    if len(video_files) < 2:
        print("Need at least 2 video files to concatenate")
        return False

    # Get durations for offset calculation
    from pyffmpegcore import FFprobeRunner
    ffprobe = FFprobeRunner()
    durations = []
    for video_file in video_files:
        try:
            metadata = ffprobe.probe(video_file)
            duration = metadata.get("duration", 0)
            durations.append(duration)
        except:
            durations.append(0)

    runner = FFmpegRunner()

    # Build input arguments
    args = []
    for video_file in video_files:
        args.extend(["-i", video_file])

    # Create complex filter for progressive crossfades
    filter_parts = []

    # Start with first video
    current_video = "[0:v]"
    current_audio = "[0:a]"

    for i in range(1, len(video_files)):
        # Calculate offset: start transition at end of previous effective content
        offset = sum(durations[:i]) - transition_duration
        if offset < 0:
            offset = 0

        # Video crossfade
        filter_parts.append(
            f"{current_video}[{i}:v]xfade=transition=fade:duration={transition_duration}:offset={offset}[v{i}];"
        )
        # Audio crossfade
        filter_parts.append(
            f"{current_audio}[{i}:a]acrossfade=d={transition_duration}:c1=tri:c2=tri[a{i}];"
        )

        current_video = f"[v{i}]"
        current_audio = f"[a{i}]"

    filter_complex = "".join(filter_parts) + f"{current_video}copy[vout];{current_audio}acopy[aout]"

    args.extend([
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-y", output_file
    ])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Videos concatenated with transitions: {output_file}")
        return True
    else:
        print(f"Failed to concatenate videos: {result.stderr}")
        return False

def get_video_info(video_files: list) -> list:
    """
    Get basic information about video files for concatenation planning.

    Args:
        video_files: List of video file paths

    Returns:
        List of dictionaries with video information
    """
    from pyffmpegcore import FFprobeRunner

    ffprobe = FFprobeRunner()
    video_info = []

    for video_file in video_files:
        try:
            metadata = ffprobe.probe(video_file)
            info = {
                "filename": os.path.basename(video_file),
                "duration": metadata.get("duration", 0),
                "size": metadata.get("size", 0),
                "video_codec": metadata.get("video", {}).get("codec", "unknown"),
                "audio_codec": metadata.get("audio", {}).get("codec", "unknown"),
                "resolution": f"{metadata.get('video', {}).get('width', 0)}x{metadata.get('video', {}).get('height', 0)}"
            }
            video_info.append(info)
        except Exception as e:
            print(f"Could not probe {video_file}: {e}")
            video_info.append({"filename": os.path.basename(video_file), "error": str(e)})

    return video_info

def main():
    """Demonstrate video concatenation capabilities."""

    # Example video files (replace with your actual files)
    video_files = [
        "clip1.mp4",
        "clip2.mp4",
        "clip3.mp4"
    ]

    # Check if files exist
    existing_files = [f for f in video_files if os.path.exists(f)]
    if len(existing_files) < 2:
        print("Example video files not found. Please create sample videos or modify the file paths.")
        print("This example shows the API usage for video concatenation.")
        return

    print("=== Video Information ===")
    video_info = get_video_info(existing_files)
    for info in video_info:
        if "error" not in info:
            print(f"{info['filename']}: {info['duration']:.1f}s, {info['resolution']}, {info['video_codec']}")
        else:
            print(f"{info['filename']}: Error - {info['error']}")

    print("\n=== Basic Concatenation (Fast, stream copy) ===")
    success = concatenate_videos_basic(existing_files, "concatenated_basic.mp4")
    if success:
        print("✓ Basic concatenation completed")

    print("\n=== Re-encoding Concatenation (Handles different codecs) ===")
    success = concatenate_videos_reencode(existing_files, "concatenated_reencoded.mp4")
    if success:
        print("✓ Re-encoding concatenation completed")

    print("\n=== Concatenation with Transitions ===")
    if len(existing_files) >= 3:  # Need at least 3 for meaningful transitions
        success = concatenate_videos_with_transitions(existing_files[:3], "concatenated_transitions.mp4", 0.5)
        if success:
            print("✓ Transition concatenation completed")
    else:
        print("Skipping transitions example (need at least 3 video files)")

    print("\nVideo concatenation examples completed!")
    print("Output files: concatenated_basic.mp4, concatenated_reencoded.mp4, concatenated_transitions.mp4")

if __name__ == "__main__":
    main()
