#!/usr/bin/env python3
"""
Example: Generate audio waveforms to visualize sound patterns.

This example demonstrates how to create waveform visualizations from audio files,
which is useful for:
- Music editing software
- Audio analysis tools
- Content preview systems
- Podcast/video editing workflows
"""

from pyffmpegcore import FFmpegRunner, FFprobeRunner
import os

def generate_waveform_image(audio_path: str, output_path: str, width: int = 800,
                           height: int = 200, colors: str = "white"):
    """
    Generate a waveform visualization image from an audio file.

    Args:
        audio_path: Path to input audio file
        output_path: Path to save the waveform image (PNG format)
        width: Image width in pixels
        height: Image height in pixels
        colors: Waveform colors (e.g., "white", "blue", "red|blue")
    """
    ffmpeg = FFmpegRunner()

    # Use FFmpeg's showwavespic filter to generate waveform
    vf_filter = f"showwavespic=s={width}x{height}:colors={colors}"

    args = [
        "-i", audio_path,
        "-filter_complex", vf_filter,
        "-frames:v", "1",  # Generate single frame
        "-y", output_path
    ]

    result = ffmpeg.run(args)

    if result.returncode == 0:
        print(f"Waveform generated: {output_path}")
        return True
    else:
        print(f"Failed to generate waveform: {result.stderr}")
        return False

def generate_detailed_waveform(audio_path: str, output_path: str, width: int = 1200,
                              height: int = 300):
    """
    Generate a detailed waveform with multiple colors and styling.

    Args:
        audio_path: Path to input audio file
        output_path: Path to save the waveform image
        width: Image width in pixels
        height: Image height in pixels
    """
    ffmpeg = FFmpegRunner()

    # Create a more detailed waveform with styling
    vf_filter = (
        f"showwavespic=s={width}x{height}:"
        "colors=blue|red|green|yellow|orange|purple:"
        "scale=lin:"
        "draw=full"
    )

    args = [
        "-i", audio_path,
        "-filter_complex", vf_filter,
        "-frames:v", "1",
        "-y", output_path
    ]

    result = ffmpeg.run(args)

    if result.returncode == 0:
        print(f"Detailed waveform generated: {output_path}")
        return True
    else:
        print(f"Failed to generate detailed waveform: {result.stderr}")
        return False

def generate_waveform_animation(audio_path: str, output_path: str, duration: float = None,
                               width: int = 800, height: int = 200):
    """
    Generate an animated waveform video showing the audio over time.

    Args:
        audio_path: Path to input audio file
        output_path: Path to save the animated waveform video
        duration: Duration to visualize (None = full audio)
        width: Video width in pixels
        height: Video height in pixels
    """
    ffmpeg = FFmpegRunner()

    # Get audio duration if not provided
    if duration is None:
        ffprobe = FFprobeRunner()
        metadata = ffprobe.probe(audio_path)
        duration = metadata.get("duration", 30)  # Default 30 seconds

    # Create animated waveform
    vf_filter = (
        f"showwaves=s={width}x{height}:"
        "mode=line:"
        "colors=blue:"
        "scale=lin:"
        "draw=full"
    )

    args = [
        "-i", audio_path,
        "-filter_complex", vf_filter,
        "-t", str(duration),  # Limit duration
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-y", output_path
    ]

    result = ffmpeg.run(args)

    if result.returncode == 0:
        print(f"Animated waveform generated: {output_path}")
        return True
    else:
        print(f"Failed to generate animated waveform: {result.stderr}")
        return False

def generate_waveform_with_metadata(audio_path: str, output_dir: str):
    """
    Generate waveform with overlaid metadata information.

    Args:
        audio_path: Path to input audio file
        output_dir: Directory to save outputs
    """
    os.makedirs(output_dir, exist_ok=True)

    # Get audio metadata
    ffprobe = FFprobeRunner()
    metadata = ffprobe.probe(audio_path)

    filename = os.path.basename(audio_path)
    duration = metadata.get("duration", 0)
    sample_rate = metadata.get("audio", {}).get("sample_rate", "Unknown")
    channels = metadata.get("audio", {}).get("channels", "Unknown")

    # Generate waveform image
    waveform_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_waveform.png")
    success = generate_waveform_image(audio_path, waveform_path, width=1000, height=300)

    if success:
        # Create metadata overlay text
        metadata_text = (
            f"File: {filename}\\n"
            f"Duration: {duration:.1f}s\\n"
            f"Sample Rate: {sample_rate} Hz\\n"
            f"Channels: {channels}"
        )

        # Add metadata overlay to the waveform
        ffmpeg = FFmpegRunner()
        final_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_waveform_with_metadata.png")

        vf_filter = f"drawtext=text='{metadata_text}':x=10:y=10:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5"

        args = [
            "-i", waveform_path,
            "-vf", vf_filter,
            "-y", final_path
        ]

        result = ffmpeg.run(args)
        if result.returncode == 0:
            print(f"Waveform with metadata generated: {final_path}")
        else:
            print(f"Failed to add metadata overlay: {result.stderr}")

def batch_generate_waveforms(audio_dir: str, output_dir: str, pattern: str = "*.mp3"):
    """
    Generate waveforms for all audio files in a directory.

    Args:
        audio_dir: Directory containing audio files
        output_dir: Directory to save waveform images
        pattern: File pattern to match (e.g., "*.mp3", "*.wav")
    """
    import glob

    os.makedirs(output_dir, exist_ok=True)

    # Find all matching audio files
    audio_files = glob.glob(os.path.join(audio_dir, pattern))

    print(f"Found {len(audio_files)} audio files")

    for audio_file in audio_files:
        filename = os.path.basename(audio_file)
        name_without_ext = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{name_without_ext}_waveform.png")

        print(f"Generating waveform for: {filename}")
        success = generate_waveform_image(audio_file, output_path, width=800, height=200)

        if success:
            print(f"✓ Generated: {output_path}")
        else:
            print(f"✗ Failed: {filename}")

def main():
    """Demonstrate waveform generation capabilities."""

    # Example 1: Basic waveform image
    print("=== Generating basic waveform ===")
    generate_waveform_image("sample.mp3", "waveform_basic.png", width=1000, height=300)

    # Example 2: Detailed waveform with multiple colors
    print("\n=== Generating detailed waveform ===")
    generate_detailed_waveform("sample.mp3", "waveform_detailed.png", width=1200, height=400)

    # Example 3: Animated waveform video
    print("\n=== Generating animated waveform ===")
    generate_waveform_animation("sample.mp3", "waveform_animation.mp4", duration=10)

    # Example 4: Waveform with metadata overlay
    print("\n=== Generating waveform with metadata ===")
    generate_waveform_with_metadata("sample.mp3", "waveforms_with_metadata/")

    # Example 5: Batch processing
    print("\n=== Batch generating waveforms ===")
    batch_generate_waveforms("audio_collection/", "waveforms_batch/", "*.mp3")

    print("\nWaveform generation examples completed!")

if __name__ == "__main__":
    main()