#!/usr/bin/env python3
"""
Example: Adjust video and audio speed/tempo.

This example demonstrates how to change the playback speed of videos and audio,
which is useful for:
- Creating time-lapse videos
- Speeding up tutorials or lectures
- Slow motion effects
- Audio tempo adjustment for music production
- Content optimization for different audiences
"""

from pyffmpegcore import FFmpegRunner, FFprobeRunner
import os


def _build_atempo_chain(speed_factor: float) -> str:
    """
    Build a chain of atempo filters to achieve the desired speed factor.

    Since atempo only supports 0.5-2.0, we chain multiple filters for factors outside this range.
    """
    if 0.5 <= speed_factor <= 2.0:
        return f"atempo={speed_factor}"

    factors = []
    current = speed_factor

    while current > 2.0:
        factors.append(2.0)
        current /= 2.0
    while current < 0.5:
        factors.append(0.5)
        current /= 0.5

    if current != 1.0:
        factors.append(current)

    return ",".join(f"atempo={f}" for f in factors)


def change_video_speed(video_file: str, output_file: str, speed_multiplier: float,
from pyffmpegcore import FFmpegRunner, FFprobeRunner
import os

def change_video_speed(video_file: str, output_file: str, speed_multiplier: float,
                      maintain_audio_pitch: bool = True) -> bool:
    """
    Change the playback speed of a video.

    Args:
        video_file: Path to input video
        output_file: Path for speed-adjusted output
        speed_multiplier: Speed factor (0.5 = half speed, 2.0 = double speed)
        maintain_audio_pitch: If True, maintain audio pitch when changing speed

    Returns:
        True if successful, False otherwise
    """
    if speed_multiplier <= 0:
        print("Speed multiplier must be positive")
        return False

    runner = FFmpegRunner()

    # Build filter complex for video and audio speed adjustment
    filter_parts = []

    # Video speed adjustment (setpts)
    video_speed = 1.0 / speed_multiplier  # FFmpeg uses reciprocal
    filter_parts.append(f"setpts={video_speed}*PTS")

    # Audio speed adjustment
    if maintain_audio_pitch:
        # Use atempo filter to change speed while maintaining pitch
        # Chain atempo filters for factors outside 0.5-2.0 range
        atempo_chain = _build_atempo_chain(speed_multiplier)
        filter_parts.append(atempo_chain)
    else:
        # Use setpts for audio too (changes pitch)
        audio_speed = 1.0 / speed_multiplier
        filter_parts.append(f"asetpts={audio_speed}*PTS")

    # Combine filters
    if len(filter_parts) == 2:
        filter_complex = f"[0:v]{filter_parts[0]}[v];[0:a]{filter_parts[1]}[a]"
        maps = ["-map", "[v]", "-map", "[a]"]
    else:
        filter_complex = f"[0:v]{filter_parts[0]}[v];[0:a]atempo={speed_multiplier}[a]"
        maps = ["-map", "[v]", "-map", "[a]"]

    args = [
        "-i", video_file,
        "-filter_complex", filter_complex,
    ] + maps + [
        "-c:v", "libx264",
        "-c:a", "aac",
        "-y", output_file
    ]

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Video speed adjusted ({speed_multiplier}x): {output_file}")
        return True
    else:
        print(f"Failed to adjust video speed: {result.stderr}")
        return False

def create_time_lapse(video_file: str, output_file: str, speed_up_factor: float = 30.0) -> bool:
    """
    Create a time-lapse video by speeding up footage.

    Args:
        video_file: Path to input video (should be slow footage)
        output_file: Path for time-lapse output
        speed_up_factor: How much to speed up (30x is typical for time-lapse)

    Returns:
        True if successful, False otherwise
    """
    return change_video_speed(video_file, output_file, speed_up_factor, maintain_audio_pitch=False)

def create_slow_motion(video_file: str, output_file: str, slow_down_factor: float = 0.5) -> bool:
    """
    Create slow motion video by slowing down footage.

    Args:
        video_file: Path to input video
        output_file: Path for slow motion output
        slow_down_factor: How much to slow down (0.5 = half speed)

    Returns:
        True if successful, False otherwise
    """
    return change_video_speed(video_file, output_file, slow_down_factor, maintain_audio_pitch=True)

def adjust_audio_tempo(audio_file: str, output_file: str, tempo_multiplier: float,
                      maintain_pitch: bool = True) -> bool:
    """
    Adjust the tempo of an audio file.

    Args:
        audio_file: Path to input audio
        output_file: Path for tempo-adjusted output
        tempo_multiplier: Tempo factor (0.5 = half tempo, 2.0 = double tempo)
        maintain_pitch: If True, maintain pitch when changing tempo

    Returns:
        True if successful, False otherwise
    """
    if tempo_multiplier <= 0:
        print("Tempo multiplier must be positive")
        return False

    runner = FFmpegRunner()

    args = ["-i", audio_file]

    if maintain_pitch:
        # Use atempo filter (maintains pitch)
        args.extend(["-filter:a", f"atempo={tempo_multiplier}"])
    else:
        # Change both tempo and pitch
        args.extend(["-filter:a", f"asetrate=44100*{tempo_multiplier},aresample=44100"])

    args.extend([
        "-c:a", "aac",
        "-b:a", "192k",
        "-y", output_file
    ])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Audio tempo adjusted ({tempo_multiplier}x): {output_file}")
        return True
    else:
        print(f"Failed to adjust audio tempo: {result.stderr}")
        return False

def create_video_summary(video_file: str, output_file: str, segment_duration: float = 5.0,
                        speed_multiplier: float = 2.0) -> bool:
    """
    Create a fast-paced summary of a long video by speeding up segments.

    Args:
        video_file: Path to input video
        output_file: Path for summary output
        segment_duration: Duration of each segment to include (seconds)
        speed_multiplier: How much to speed up the summary

    Returns:
        True if successful, False otherwise
    """
    # Get video duration
    ffprobe = FFprobeRunner()
    metadata = ffprobe.probe(video_file)
    duration = metadata.get("duration", 0)

    if duration == 0:
        print("Could not determine video duration")
        return False

    # Create segments at regular intervals
    segments = []
    interval = duration / 10  # Sample 10 segments throughout the video

    for i in range(10):
        start_time = i * interval
        if start_time + segment_duration > duration:
            break
        segments.append((start_time, segment_duration))

    if not segments:
        print("Video too short for summary creation")
        return False

    runner = FFmpegRunner()

    # Build complex filter for extracting and concatenating segments
    filter_parts = []

    # Add input
    args = ["-i", video_file]

    # Create filter for each segment
    for i, (start_time, seg_duration) in enumerate(segments):
        # Extract segment and speed it up
        video_speed = 1.0 / speed_multiplier
        audio_speed = speed_multiplier

        filter_parts.append(
            f"[0:v]trim={start_time}:{start_time + seg_duration},setpts={video_speed}*PTS[v{i}];"
            f"[0:a]atrim={start_time}:{start_time + seg_duration},atempo={audio_speed}[a{i}];"
        )

    # Concatenate all segments
    video_concat = "".join([f"[v{i}]" for i in range(len(segments))])
    audio_concat = "".join([f"[a{i}]" for i in range(len(segments))])

    filter_parts.append(
        f"{video_concat}concat=n={len(segments)}:v=1:a=0[vout];"
        f"{audio_concat}concat=n={len(segments)}:v=0:a=1[aout]"
    )

    filter_complex = "".join(filter_parts)

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
        print(f"Video summary created: {output_file}")
        return True
    else:
        print(f"Failed to create video summary: {result.stderr}")
        return False

def reverse_video(video_file: str, output_file: str) -> bool:
    """
    Create a reversed version of a video (play backwards).

    Args:
        video_file: Path to input video
        output_file: Path for reversed output

    Returns:
        True if successful, False otherwise
    """
    runner = FFmpegRunner()

    # Reverse both video and audio
    filter_complex = (
        "[0:v]reverse[rvid];"
        "[0:a]areverse[raid]"
    )

    args = [
        "-i", video_file,
        "-filter_complex", filter_complex,
        "-map", "[rvid]",
        "-map", "[raid]",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-y", output_file
    ]

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Video reversed: {output_file}")
        return True
    else:
        print(f"Failed to reverse video: {result.stderr}")
        return False

def get_video_info(video_file: str) -> dict:
    """
    Get basic information about a video file.

    Args:
        video_file: Path to video file

    Returns:
        Dictionary with video information
    """
    ffprobe = FFprobeRunner()

    try:
        metadata = ffprobe.probe(video_file)
        return {
            "duration": metadata.get("duration", 0),
            "width": metadata.get("video", {}).get("width", 0),
            "height": metadata.get("video", {}).get("height", 0),
            "frame_rate": metadata.get("video", {}).get("fps", 0),
            "video_codec": metadata.get("video", {}).get("codec", "unknown"),
            "audio_codec": metadata.get("audio", {}).get("codec", "unknown")
        }
    except Exception as e:
        print(f"Could not probe video: {e}")
        return {}

def main():
    """Demonstrate video and audio speed adjustment capabilities."""

    # Example video file
    video_file = "sample.mp4"
    audio_file = "sample.mp3"

    if not os.path.exists(video_file):
        print(f"Example video file '{video_file}' not found.")
        print("This example shows the API usage for speed adjustment.")
        return

    print("=== Video Information ===")
    info = get_video_info(video_file)
    if info:
        print(f"Duration: {info['duration']:.1f}s")
        print(f"Resolution: {info['width']}x{info['height']}")
        print(f"Video codec: {info['video_codec']}, Audio codec: {info['audio_codec']}")

    print("\n=== Speed Up Video (2x) ===")
    success = change_video_speed(video_file, "sped_up_2x.mp4", 2.0, maintain_audio_pitch=True)
    if success:
        print("✓ Video sped up 2x with maintained pitch")

    print("\n=== Slow Down Video (0.5x) ===")
    success = change_video_speed(video_file, "slow_motion.mp4", 0.5, maintain_audio_pitch=True)
    if success:
        print("✓ Slow motion video created")

    print("\n=== Time-lapse Effect (10x speed) ===")
    success = create_time_lapse(video_file, "timelapse.mp4", 10.0)
    if success:
        print("✓ Time-lapse video created")

    print("\n=== Reverse Video ===")
    success = reverse_video(video_file, "reversed.mp4")
    if success:
        print("✓ Video reversed")

    print("\n=== Video Summary (Fast-paced highlights) ===")
    success = create_video_summary(video_file, "summary.mp4", segment_duration=3.0, speed_multiplier=3.0)
    if success:
        print("✓ Video summary created")

    if os.path.exists(audio_file):
        print("\n=== Adjust Audio Tempo ===")
        success = adjust_audio_tempo(audio_file, "tempo_up.mp3", 1.5, maintain_pitch=True)
        if success:
            print("✓ Audio tempo increased by 50% with maintained pitch")

        success = adjust_audio_tempo(audio_file, "tempo_down.mp3", 0.8, maintain_pitch=True)
        if success:
            print("✓ Audio tempo decreased by 20% with maintained pitch")
    else:
        print(f"\nAudio file '{audio_file}' not found - skipping audio tempo examples")

    print("\nSpeed adjustment examples completed!")
    print("Output files: sped_up_2x.mp4, slow_motion.mp4, timelapse.mp4,")
    print("              reversed.mp4, summary.mp4, tempo_up.mp3, tempo_down.mp3")

if __name__ == "__main__":
    main()