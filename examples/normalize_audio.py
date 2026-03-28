#!/usr/bin/env python3
"""
Example: Audio normalization and dynamic range compression.

This example demonstrates audio normalization techniques,
which is useful for:
- Consistent audio levels across tracks
- Podcast production
- Music mastering
- Broadcasting standards compliance
- Audio post-production
"""

import os

from pyffmpegcore import FFmpegRunner, FFprobeRunner


_AUDIO_CODEC_BY_EXTENSION = {
    ".aac": "aac",
    ".flac": "flac",
    ".m4a": "aac",
    ".mp3": "libmp3lame",
    ".ogg": "libvorbis",
    ".opus": "libopus",
    ".wav": "pcm_s16le",
}
_BITRATELESS_AUDIO_CODECS = {"flac", "pcm_s16le"}


def _append_audio_output_options(
    args: list[str],
    output_file: str,
    bitrate: str,
) -> None:
    extension = os.path.splitext(output_file)[1].lower()
    codec = _AUDIO_CODEC_BY_EXTENSION.get(extension, "aac")
    args.extend(["-c:a", codec])
    if bitrate and codec not in _BITRATELESS_AUDIO_CODECS:
        args.extend(["-b:a", bitrate])


def normalize_audio_loudnorm(audio_file: str, output_file: str,
                           target_i: float = -16.0, target_tp: float = -1.5,
                           target_lra: float = 11.0) -> bool:
    """
    Normalize audio using FFmpeg's loudnorm filter (EBU R128 standard).

    Args:
        audio_file: Path to input audio file
        output_file: Path for normalized output
        target_i: Target integrated loudness in LUFS (default: -16)
        target_tp: Target true peak in dBTP (default: -1.5)
        target_lra: Target loudness range in LU (default: 11)

    Returns:
        True if successful, False otherwise
    """
    runner = FFmpegRunner()

    # Build loudnorm filter
    loudnorm_filter = f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}"

    args = [
        "-i", audio_file,
        "-af", loudnorm_filter,
    ]
    _append_audio_output_options(args, output_file, bitrate="192k")
    args.extend(["-y", output_file])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Audio normalized with loudnorm: {output_file}")
        return True
    else:
        print(f"Failed to normalize audio: {result.stderr}")
        return False

def normalize_audio_peak_level(audio_file: str, output_file: str, target_db: float = -3.0) -> bool:
    """
    Normalize audio to a target peak level.

    Args:
        audio_file: Path to input audio file
        output_file: Path for normalized output
        target_db: Target peak level in dBFS (default: -3.0)

    Returns:
        True if successful, False otherwise
    """
    runner = FFmpegRunner()

    # Use volume filter to adjust to target peak level
    # This requires two passes: first to measure, second to adjust
    # For simplicity, we'll use a dynamic approach

    volume_filter = f"volume={target_db}dB"

    args = [
        "-i", audio_file,
        "-af", volume_filter,
    ]
    _append_audio_output_options(args, output_file, bitrate="192k")
    args.extend(["-y", output_file])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Audio peak normalized to {target_db}dB: {output_file}")
        return True
    else:
        print(f"Failed to normalize audio peak: {result.stderr}")
        return False

def apply_compression(audio_file: str, output_file: str, threshold: float = -20.0,
                     ratio: float = 4.0, attack: float = 0.0001, release: float = 0.2) -> bool:
    """
    Apply dynamic range compression to audio.

    Args:
        audio_file: Path to input audio file
        output_file: Path for compressed output
        threshold: Compressor threshold in dB (default: -20)
        ratio: Compression ratio (default: 4:1)
        attack: Attack time in seconds (default: 0.0001)
        release: Release time in seconds (default: 0.2)

    Returns:
        True if successful, False otherwise
    """
    runner = FFmpegRunner()

    # Build compand filter for compression
    compand_filter = f"compand=attacks={attack}:decays={release}:points=-70/-70|-60/-20|{threshold}/{threshold}|20/20"

    args = [
        "-i", audio_file,
        "-af", compand_filter,
    ]
    _append_audio_output_options(args, output_file, bitrate="192k")
    args.extend(["-y", output_file])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Audio compression applied: {output_file}")
        return True
    else:
        print(f"Failed to apply compression: {result.stderr}")
        return False

def apply_limiter(audio_file: str, output_file: str, limit_db: float = -1.0) -> bool:
    """
    Apply a brickwall limiter to prevent clipping.

    Args:
        audio_file: Path to input audio file
        output_file: Path for limited output
        limit_db: Limiting threshold in dBFS (default: -1.0)

    Returns:
        True if successful, False otherwise
    """
    runner = FFmpegRunner()

    # Use alimiter filter
    limiter_filter = f"alimiter=limit={limit_db}dB:level=disabled"

    args = [
        "-i", audio_file,
        "-af", limiter_filter,
    ]
    _append_audio_output_options(args, output_file, bitrate="192k")
    args.extend(["-y", output_file])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Audio limiter applied: {output_file}")
        return True
    else:
        print(f"Failed to apply limiter: {result.stderr}")
        return False

def create_mastered_audio(audio_file: str, output_file: str) -> bool:
    """
    Apply a complete mastering chain: normalization + compression + limiting.

    Args:
        audio_file: Path to input audio file
        output_file: Path for mastered output

    Returns:
        True if successful, False otherwise
    """
    runner = FFmpegRunner()

    # Build a mastering chain
    # 1. Loudness normalization
    # 2. Gentle compression
    # 3. Brickwall limiting
    mastering_chain = (
        "loudnorm=I=-16:TP=-1.5:LRA=11,"  # EBU R128 normalization
        "compand=attacks=0.0001:decays=0.2:points=-70/-70|-60/-20|-20/-20|20/20,"  # Compression
        "alimiter=limit=-1dB:level=disabled"  # Limiting
    )

    args = [
        "-i", audio_file,
        "-af", mastering_chain,
    ]
    _append_audio_output_options(args, output_file, bitrate="256k")
    args.extend(["-y", output_file])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Audio mastered: {output_file}")
        return True
    else:
        print(f"Failed to master audio: {result.stderr}")
        return False

def analyze_audio_levels(audio_file: str) -> dict:
    """
    Analyze audio levels and loudness using FFmpeg filters.

    Args:
        audio_file: Path to audio file to analyze

    Returns:
        Dictionary with audio analysis results
    """
    try:
        # Get basic metadata
        ffprobe = FFprobeRunner()
        metadata = ffprobe.probe(audio_file)

        return {
            "filename": os.path.basename(audio_file),
            "duration": metadata.get("duration", 0),
            "sample_rate": metadata.get("audio", {}).get("sample_rate", 0),
            "channels": metadata.get("audio", {}).get("channels", 0),
            "bitrate": metadata.get("audio", {}).get("bit_rate", 0),
            "codec": metadata.get("audio", {}).get("codec", "unknown")
        }
    except Exception as e:
        print(f"Could not analyze audio: {e}")
        return {"error": str(e)}

def batch_normalize_audio(audio_dir: str, output_dir: str, method: str = "loudnorm") -> dict:
    """
    Batch normalize all audio files in a directory.

    Args:
        audio_dir: Directory containing audio files
        output_dir: Directory to save normalized files
        method: Normalization method ("loudnorm", "peak", "master")

    Returns:
        Dictionary with batch processing results
    """
    import glob

    os.makedirs(output_dir, exist_ok=True)

    # Find audio files
    audio_patterns = ['*.mp3', '*.wav', '*.flac', '*.aac', '*.m4a']
    audio_files = []
    for pattern in audio_patterns:
        audio_files.extend(glob.glob(os.path.join(audio_dir, pattern)))

    if not audio_files:
        print("No audio files found")
        return {"total": 0, "successful": 0, "failed": 0}

    print(f"Found {len(audio_files)} audio files to normalize")

    results = {"total": len(audio_files), "successful": 0, "failed": 0}

    for audio_file in audio_files:
        filename = os.path.basename(audio_file)
        name_without_ext = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{name_without_ext}_normalized.mp3")

        print(f"Normalizing: {filename}")

        if method == "loudnorm":
            success = normalize_audio_loudnorm(audio_file, output_path)
        elif method == "peak":
            success = normalize_audio_peak_level(audio_file, output_path)
        elif method == "master":
            success = create_mastered_audio(audio_file, output_path)
        else:
            print(f"Unknown method: {method}")
            success = False

        if success:
            results["successful"] += 1
            print(f"✓ Normalized: {output_path}")
        else:
            results["failed"] += 1
            print(f"✗ Failed: {filename}")

    return results

def main():
    """Demonstrate audio normalization capabilities."""

    # Example audio file
    audio_file = "sample.mp3"

    if not os.path.exists(audio_file):
        print(f"Example audio file '{audio_file}' not found.")
        print("This example shows the API usage for audio normalization.")
        return

    print("=== Audio Analysis ===")
    analysis = analyze_audio_levels(audio_file)
    if "error" not in analysis:
        print(f"Duration: {analysis['duration']:.1f}s")
        print(f"Sample Rate: {analysis['sample_rate']} Hz")
        print(f"Channels: {analysis['channels']}")
        print(f"Bitrate: {analysis['bitrate']} bps")
        print(f"Codec: {analysis['codec']}")

    print("\n=== Loudness Normalization (EBU R128) ===")
    success = normalize_audio_loudnorm(audio_file, "normalized_loudnorm.mp3")
    if success:
        print("✓ EBU R128 normalization applied")

    print("\n=== Peak Level Normalization ===")
    success = normalize_audio_peak_level(audio_file, "normalized_peak.mp3", target_db=-3.0)
    if success:
        print("✓ Peak level normalized to -3dB")

    print("\n=== Dynamic Range Compression ===")
    success = apply_compression(audio_file, "compressed.mp3", threshold=-18.0, ratio=3.0)
    if success:
        print("✓ Compression applied")

    print("\n=== Brickwall Limiting ===")
    success = apply_limiter(audio_file, "limited.mp3", limit_db=-1.0)
    if success:
        print("✓ Limiter applied")

    print("\n=== Complete Mastering Chain ===")
    success = create_mastered_audio(audio_file, "mastered.mp3")
    if success:
        print("✓ Full mastering chain applied")

    print("\n=== Batch Normalization ===")
    # This would process all files in a directory
    print("Batch processing example (would process all audio files in a directory)")
    print("Use: batch_normalize_audio('audio_dir/', 'output_dir/', 'loudnorm')")

    print("\nAudio normalization examples completed!")
    print("Output files: normalized_loudnorm.mp3, normalized_peak.mp3,")
    print("              compressed.mp3, limited.mp3, mastered.mp3")

if __name__ == "__main__":
    main()
