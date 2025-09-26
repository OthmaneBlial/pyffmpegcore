#!/usr/bin/env python3
"""
Example: Extract, burn, and manipulate subtitles in videos.

This example demonstrates subtitle handling capabilities,
which is useful for:
- Adding subtitles to videos
- Extracting subtitles for translation
- Burning subtitles permanently into video
- Converting between subtitle formats
- Multi-language subtitle support
"""

from pyffmpegcore import FFmpegRunner, FFprobeRunner
import os

def extract_subtitles(video_file: str, output_file: str, stream_index: int = 0) -> bool:
    """
    Extract subtitles from a video file.

    Args:
        video_file: Path to video file with subtitles
        output_file: Path for extracted subtitles (e.g., 'subs.srt' or 'subs.vtt')
        stream_index: Index of subtitle stream to extract (0-based)

    Returns:
        True if successful, False otherwise
    """
    runner = FFmpegRunner()

    args = [
        "-i", video_file,
        "-map", f"0:s:{stream_index}",  # Extract specific subtitle stream
        "-y", output_file
    ]

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Subtitles extracted: {output_file}")
        return True
    else:
        print(f"Failed to extract subtitles: {result.stderr}")
        return False

def burn_subtitles(video_file: str, subtitle_file: str, output_file: str,
                  font_size: int = 24, font_color: str = "&HFFFFFF") -> bool:
    """
    Burn subtitles permanently into a video file.

    Args:
        video_file: Path to input video
        subtitle_file: Path to subtitle file
        output_file: Path for output video with burned subtitles
        font_size: Font size for subtitles
        font_color: Font color in ASS BGR hex format (e.g., "&HFFFFFF" for white)

    Returns:
        True if successful, False otherwise
    """
    runner = FFmpegRunner()

    # Escape path for Windows
    escaped_path = subtitle_file.replace('\\', '\\\\').replace(':', '\\:')

    # Build subtitle filter with proper quoting for Windows
    subtitle_filter = f"subtitles=\"{escaped_path}\":force_style='FontSize={font_size},PrimaryColour={font_color}'"

    args = [
        "-i", video_file,
        "-vf", subtitle_filter,
        "-c:a", "copy",  # Copy audio without re-encoding
        "-y", output_file
    ]

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Subtitles burned into video: {output_file}")
        return True
    else:
        print(f"Failed to burn subtitles: {result.stderr}")
        return False

def add_subtitle_track(video_file: str, subtitle_file: str, output_file: str,
                      language: str = "eng") -> bool:
    """
    Add subtitles as a separate track (not burned) to a video file.

    Args:
        video_file: Path to input video
        subtitle_file: Path to subtitle file
        output_file: Path for output video with subtitle track
        language: Language code for subtitle track

    Returns:
        True if successful, False otherwise
    """
    runner = FFmpegRunner()

    args = [
        "-i", video_file,
        "-i", subtitle_file,
        "-c:v", "copy",  # Copy video
        "-c:a", "copy",  # Copy audio
        "-c:s", "mov_text",  # Subtitle codec for MP4
        "-metadata:s:s:0", f"language={language}",
        "-y", output_file
    ]

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Subtitle track added: {output_file}")
        return True
    else:
        print(f"Failed to add subtitle track: {result.stderr}")
        return False

def convert_subtitle_format(input_file: str, output_file: str) -> bool:
    """
    Convert subtitles between different formats (e.g., SRT to VTT).

    Args:
        input_file: Path to input subtitle file
        output_file: Path for converted subtitle file

    Returns:
        True if successful, False otherwise
    """
    runner = FFmpegRunner()

    args = [
        "-i", input_file,
        "-y", output_file
    ]

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Subtitles converted: {output_file}")
        return True
    else:
        print(f"Failed to convert subtitles: {result.stderr}")
        return False

def create_multi_language_subtitles(video_file: str, subtitle_files: dict,
                                   output_file: str) -> bool:
    """
    Add multiple subtitle tracks in different languages to a video.

    Args:
        video_file: Path to input video
        subtitle_files: Dict mapping language codes to subtitle file paths
        output_file: Path for output video with multiple subtitle tracks

    Returns:
        True if successful, False otherwise
    """
    runner = FFmpegRunner()

    # Build input arguments
    args = ["-i", video_file]
    for subtitle_file in subtitle_files.values():
        args.extend(["-i", subtitle_file])

    # Copy video and audio
    args.extend(["-c:v", "copy", "-c:a", "copy"])

    # Add each subtitle track
    for i, (lang_code, subtitle_file) in enumerate(subtitle_files.items()):
        args.extend([
            "-c:s", "mov_text",
            f"-metadata:s:s:{i}", f"language={lang_code}",
            f"-metadata:s:s:{i}", f"title={lang_code.upper()}"
        ])

    args.extend(["-y", output_file])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Multi-language subtitles added: {output_file}")
        return True
    else:
        print(f"Failed to add multi-language subtitles: {result.stderr}")
        return False

def extract_hardcoded_subtitles(video_file: str, output_file: str) -> bool:
    """
    Attempt to extract hardcoded/burned subtitles using OCR (experimental).

    Note: This is not reliable and requires additional OCR tools.
    For proper subtitle extraction, use files with embedded subtitle tracks.

    Args:
        video_file: Path to video with hardcoded subtitles
        output_file: Path for extracted subtitle file

    Returns:
        True if successful, False otherwise
    """
    print("Warning: Extracting hardcoded subtitles requires OCR tools and is not reliable.")
    print("For best results, use videos with embedded subtitle tracks.")

    runner = FFmpegRunner()

    # This is a placeholder - actual OCR subtitle extraction would require
    # additional tools like Tesseract OCR and is quite complex
    # For now, we'll just show the approach

    print("Hardcoded subtitle extraction requires additional OCR tools.")
    print("Consider using videos with embedded subtitle streams instead.")
    return False

def get_subtitle_info(video_file: str) -> list:
    """
    Get information about subtitle streams in a video file.

    Args:
        video_file: Path to video file

    Returns:
        List of dictionaries with subtitle stream information
    """
    ffprobe = FFprobeRunner()

    try:
        metadata = ffprobe.probe(video_file)
        subtitle_streams = []

        for stream in metadata.get("streams", []):
            if stream.get("codec_type") == "subtitle":
                subtitle_info = {
                    "index": stream.get("index"),
                    "codec": stream.get("codec_name"),
                    "language": stream.get("tags", {}).get("language", "und"),
                    "title": stream.get("tags", {}).get("title", "")
                }
                subtitle_streams.append(subtitle_info)

        return subtitle_streams

    except Exception as e:
        print(f"Could not probe video file: {e}")
        return []

def main():
    """Demonstrate subtitle handling capabilities."""

    # Example video file with subtitles
    video_file = "video_with_subs.mkv"
    subtitle_file = "subtitles.srt"

    if not os.path.exists(video_file):
        print(f"Example video file '{video_file}' not found.")
        print("This example shows the API usage for subtitle handling.")
        print("Please create sample files or modify the file paths.")
        return

    print("=== Subtitle Stream Information ===")
    subtitle_streams = get_subtitle_info(video_file)
    if subtitle_streams:
        for stream in subtitle_streams:
            print(f"Stream {stream['index']}: {stream['codec']} ({stream['language']}) - {stream['title']}")
    else:
        print("No subtitle streams found in video file")

    print("\n=== Extract Subtitles ===")
    if subtitle_streams:
        success = extract_subtitles(video_file, "extracted_subtitles.srt", stream_index=0)
        if success:
            print("✓ Subtitles extracted")
    else:
        print("No subtitle streams to extract")

    print("\n=== Burn Subtitles into Video ===")
    if os.path.exists(subtitle_file):
        success = burn_subtitles(video_file, subtitle_file, "video_with_burned_subs.mp4",
                               font_size=32, font_color="&H00FFFF")  # Yellow in BGR
        if success:
            print("✓ Subtitles burned into video")
    else:
        print(f"Subtitle file '{subtitle_file}' not found")

    print("\n=== Add Subtitle Track ===")
    if os.path.exists(subtitle_file):
        success = add_subtitle_track(video_file, subtitle_file, "video_with_sub_track.mp4",
                                   language="eng")
        if success:
            print("✓ Subtitle track added")
    else:
        print(f"Subtitle file '{subtitle_file}' not found")

    print("\n=== Convert Subtitle Format ===")
    if os.path.exists("subtitles.srt"):
        success = convert_subtitle_format("subtitles.srt", "subtitles.vtt")
        if success:
            print("✓ Subtitles converted to VTT format")

    print("\n=== Multi-Language Subtitles ===")
    # Example with multiple languages
    multi_subs = {
        "eng": "subtitles_en.srt",
        "spa": "subtitles_es.srt",
        "fra": "subtitles_fr.srt"
    }

    # Check if any subtitle files exist
    existing_subs = {lang: path for lang, path in multi_subs.items() if os.path.exists(path)}

    if existing_subs:
        success = create_multi_language_subtitles(video_file, existing_subs,
                                                "video_multi_lang_subs.mp4")
        if success:
            print("✓ Multi-language subtitles added")
    else:
        print("No subtitle files found for multi-language example")

    print("\nSubtitle handling examples completed!")
    print("Output files: extracted_subtitles.srt, video_with_burned_subs.mp4,")
    print("              video_with_sub_track.mp4, subtitles.vtt, video_multi_lang_subs.mp4")

if __name__ == "__main__":
    main()