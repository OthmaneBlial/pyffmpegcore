#!/usr/bin/env python3
"""
Example: Compress a video with progress tracking.
"""

from pyffmpegcore import FFmpegRunner, FFprobeRunner, ProgressCallback

def main():
    # Initialize runners
    ffmpeg = FFmpegRunner()
    ffprobe = FFprobeRunner()

    # Get input file duration for progress calculation
    duration = ffprobe.get_duration("input.mp4")
    print(f"Input duration: {duration:.2f} seconds")

    # Create progress callback
    progress_callback = ProgressCallback(total_duration=duration)
    
    # Compress video with progress tracking
    result = ffmpeg.compress(
        input_file="input.mp4",
        output_file="compressed.mp4",
        crf=28,  # Higher CRF = more compression
        progress_callback=progress_callback
    )

    if result.returncode == 0:
        print("Compression successful!")
    else:
        print(f"Compression failed: {result.stderr}")

if __name__ == "__main__":
    main()