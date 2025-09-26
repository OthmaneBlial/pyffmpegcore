#!/usr/bin/env python3
"""
Example: Convert a video file to MP4 format.
"""

from pyffmpegcore import FFmpegRunner

def main():
    # Initialize FFmpeg runner
    ffmpeg = FFmpegRunner()

    # Convert video to MP4
    result = ffmpeg.convert(
        input_file="input.avi",
        output_file="output.mp4",
        video_codec="libx264",
        audio_codec="aac"
    )

    if result.returncode == 0:
        print("Conversion successful!")
    else:
        print(f"Conversion failed: {result.stderr}")

if __name__ == "__main__":
    main()