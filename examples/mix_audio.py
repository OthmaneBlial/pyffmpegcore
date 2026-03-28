#!/usr/bin/env python3
"""
Example: Mix and merge multiple audio files.

This example demonstrates how to combine multiple audio files through mixing/merging,
which is useful for:
- Creating music mashups
- Audio post-production
- Podcast editing
- Sound design
- Background music mixing
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


def _select_audio_codec(output_file: str) -> str:
    extension = os.path.splitext(output_file)[1].lower()
    return _AUDIO_CODEC_BY_EXTENSION.get(extension, "aac")


def _append_audio_output_options(
    args: list[str],
    output_file: str,
    bitrate: str,
) -> None:
    codec = _select_audio_codec(output_file)
    args.extend(["-c:a", codec])
    if bitrate and codec not in _BITRATELESS_AUDIO_CODECS:
        args.extend(["-b:a", bitrate])


def _collect_valid_audio_inputs(
    audio_files: list,
    volumes: list | None = None,
) -> tuple[list[str], list[float] | None]:
    ffprobe = FFprobeRunner()
    valid_files = []
    valid_volumes = [] if volumes is not None else None

    for index, audio_file in enumerate(audio_files):
        try:
            metadata = ffprobe.probe(audio_file)
        except Exception as exc:
            print(f"Warning: Could not probe {audio_file}: {exc}, skipping")
            continue

        if not metadata.get("audio"):
            print(f"Warning: {audio_file} has no audio stream, skipping")
            continue

        valid_files.append(audio_file)
        if valid_volumes is not None:
            valid_volumes.append(volumes[index])

    return valid_files, valid_volumes


def mix_audio_files(audio_files: list, output_file: str, volumes: list = None) -> bool:
    """
    Mix multiple audio files together with optional volume control.

    Args:
        audio_files: List of audio file paths to mix
        output_file: Path for the mixed output audio
        volumes: Optional list of volume multipliers (0.0-1.0) for each input

    Returns:
        True if successful, False otherwise
    """
    if len(audio_files) < 2:
        print("Need at least 2 audio files to mix")
        return False
    if volumes is not None and len(volumes) != len(audio_files):
        print("Volumes list must match the number of input files")
        return False
    if volumes is not None and any(volume <= 0 for volume in volumes):
        print("Volumes must be positive values")
        return False

    valid_files, valid_volumes = _collect_valid_audio_inputs(audio_files, volumes)

    if len(valid_files) < 2:
        print("Need at least 2 valid audio files to mix")
        return False

    runner = FFmpegRunner()
    args = []
    for audio_file in valid_files:
        args.extend(["-i", audio_file])

    filter_parts = []
    for i, _audio_file in enumerate(valid_files):
        vol = valid_volumes[i] if valid_volumes is not None else 1.0
        if vol != 1.0:
            filter_parts.append(f"[{i}:a]volume={vol}[a{i}]")
        else:
            filter_parts.append(f"[{i}:a]anull[a{i}]")

    mix_inputs = "".join(f"[a{i}]" for i in range(len(valid_files)))
    filter_parts.append(
        f"{mix_inputs}amix=inputs={len(valid_files)}:duration=longest:normalize=0[aout]"
    )
    filter_complex = ";".join(filter_parts)

    args.extend([
        "-filter_complex", filter_complex,
        "-map", "[aout]",
    ])
    _append_audio_output_options(args, output_file, bitrate="192k")
    args.extend(["-y", output_file])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Audio files mixed successfully: {output_file}")
        return True

    print(f"Failed to mix audio files: {result.stderr}")
    return False

def merge_audio_sequentially(audio_files: list, output_file: str) -> bool:
    """
    Merge audio files sequentially (one after another) rather than mixing simultaneously.

    Args:
        audio_files: List of audio file paths to concatenate
        output_file: Path for the merged output audio

    Returns:
        True if successful, False otherwise
    """
    if len(audio_files) < 2:
        print("Need at least 2 audio files to merge")
        return False

    valid_files, _ = _collect_valid_audio_inputs(audio_files)
    if len(valid_files) < 2:
        print("Need at least 2 valid audio files to merge")
        return False

    runner = FFmpegRunner()
    args = []
    for audio_file in valid_files:
        args.extend(["-i", audio_file])

    concat_inputs = "".join(f"[{i}:a]" for i in range(len(valid_files)))
    filter_complex = f"{concat_inputs}concat=n={len(valid_files)}:v=0:a=1[aout]"

    args.extend([
        "-filter_complex", filter_complex,
        "-map", "[aout]",
    ])
    _append_audio_output_options(args, output_file, bitrate="192k")
    args.extend(["-y", output_file])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Audio files merged sequentially: {output_file}")
        return True

    print(f"Failed to merge audio files: {result.stderr}")
    return False

def create_audio_mashup(audio_files: list, output_file: str,
                       crossfade_duration: float = 2.0) -> bool:
    """
    Create an audio mashup with crossfades between tracks.

    Args:
        audio_files: List of audio file paths
        output_file: Path for the mashup output
        crossfade_duration: Duration of crossfade between tracks in seconds

    Returns:
        True if successful, False otherwise
    """
    if len(audio_files) < 2:
        print("Need at least 2 audio files for mashup")
        return False
    if crossfade_duration <= 0:
        print("Crossfade duration must be positive")
        return False

    valid_files, _ = _collect_valid_audio_inputs(audio_files)
    if len(valid_files) < 2:
        print("Need at least 2 valid audio files for mashup")
        return False

    runner = FFmpegRunner()
    args = []
    for audio_file in valid_files:
        args.extend(["-i", audio_file])

    filter_parts = []
    current_label = "[0:a]"
    for i in range(1, len(valid_files)):
        next_label = f"[a{i}]"
        filter_parts.append(
            f"{current_label}[{i}:a]acrossfade="
            f"d={crossfade_duration}:c1=tri:c2=tri{next_label}"
        )
        current_label = next_label
    filter_complex = ";".join(filter_parts)

    args.extend([
        "-filter_complex", filter_complex,
        "-map", current_label,
    ])
    _append_audio_output_options(args, output_file, bitrate="256k")
    args.extend(["-y", output_file])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Audio mashup created: {output_file}")
        return True

    print(f"Failed to create audio mashup: {result.stderr}")
    return False

def add_background_music(main_audio: str, background_audio: str, output_file: str,
                        bg_volume: float = 0.3) -> bool:
    """
    Mix main audio with background music at a lower volume.

    Args:
        main_audio: Path to main audio file
        background_audio: Path to background music file
        output_file: Path for the mixed output
        bg_volume: Volume multiplier for background music (0.0-1.0)

    Returns:
        True if successful, False otherwise
    """
    valid_files, _ = _collect_valid_audio_inputs([main_audio, background_audio])
    if len(valid_files) != 2:
        print("Both inputs must contain audio streams")
        return False

    runner = FFmpegRunner()
    args = ["-i", valid_files[0], "-i", valid_files[1]]

    filter_complex = (
        f"[1:a]volume={bg_volume}[bg];"
        "[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0[aout]"
    )

    args.extend([
        "-filter_complex", filter_complex,
        "-map", "[aout]",
    ])
    _append_audio_output_options(args, output_file, bitrate="192k")
    args.extend(["-y", output_file])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Background music added: {output_file}")
        return True

    print(f"Failed to add background music: {result.stderr}")
    return False

def create_stereo_from_mono(left_audio: str, right_audio: str, output_file: str) -> bool:
    """
    Create stereo audio by combining two mono files.

    Args:
        left_audio: Path to left channel audio
        right_audio: Path to right channel audio
        output_file: Path for stereo output

    Returns:
        True if successful, False otherwise
    """
    runner = FFmpegRunner()

    args = ["-i", left_audio, "-i", right_audio]

    # Join mono channels into stereo
    filter_complex = "[0:a][1:a]join=inputs=2:channel_layout=stereo[aout]"

    args.extend([
        "-filter_complex", filter_complex,
        "-map", "[aout]",
    ])
    _append_audio_output_options(args, output_file, bitrate="192k")
    args.extend(["-y", output_file])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Stereo audio created: {output_file}")
        return True

    print(f"Failed to create stereo audio: {result.stderr}")
    return False

def get_audio_info(audio_files: list) -> list:
    """
    Get information about audio files for mixing planning.

    Args:
        audio_files: List of audio file paths

    Returns:
        List of dictionaries with audio information
    """
    ffprobe = FFprobeRunner()
    audio_info = []

    for audio_file in audio_files:
        try:
            metadata = ffprobe.probe(audio_file)
            info = {
                "filename": os.path.basename(audio_file),
                "duration": metadata.get("duration", 0),
                "format": metadata.get("format_name", "unknown"),
                "audio_codec": metadata.get("audio", {}).get("codec", "unknown"),
                "sample_rate": metadata.get("audio", {}).get("sample_rate", 0),
                "channels": metadata.get("audio", {}).get("channels", 0),
                "bitrate": metadata.get("audio", {}).get("bit_rate", 0)
            }
            audio_info.append(info)
        except Exception as e:
            print(f"Could not probe {audio_file}: {e}")
            audio_info.append({"filename": os.path.basename(audio_file), "error": str(e)})

    return audio_info

def main():
    """Demonstrate audio mixing and merging capabilities."""

    # Example audio files (replace with your actual files)
    audio_files = [
        "track1.mp3",
        "track2.mp3",
        "track3.mp3"
    ]

    # Check if files exist
    existing_files = [f for f in audio_files if os.path.exists(f)]
    if len(existing_files) < 2:
        print("Example audio files not found. Please create sample audio files or modify the file paths.")
        print("This example shows the API usage for audio mixing.")
        return

    print("=== Audio Information ===")
    audio_info = get_audio_info(existing_files)
    for info in audio_info:
        if "error" not in info:
            print(f"{info['filename']}: {info['duration']:.1f}s, {info['audio_codec']}, {info['channels']}ch, {info['sample_rate']}Hz")
        else:
            print(f"{info['filename']}: Error - {info['error']}")

    print("\n=== Simultaneous Mixing ===")
    volumes = [1.0, 0.7, 0.5]  # Different volumes for each track
    success = mix_audio_files(existing_files, "mixed_audio.mp3", volumes[:len(existing_files)])
    if success:
        print("✓ Audio mixing completed")

    print("\n=== Sequential Merging ===")
    success = merge_audio_sequentially(existing_files, "merged_audio.mp3")
    if success:
        print("✓ Sequential merging completed")

    print("\n=== Audio Mashup with Crossfades ===")
    success = create_audio_mashup(existing_files, "mashup.mp3", crossfade_duration=3.0)
    if success:
        print("✓ Audio mashup completed")

    print("\n=== Background Music Addition ===")
    if len(existing_files) >= 2:
        success = add_background_music(existing_files[0], existing_files[1], "with_background.mp3", bg_volume=0.2)
        if success:
            print("✓ Background music added")

    print("\n=== Stereo Creation from Mono ===")
    # This would need actual mono files
    # success = create_stereo_from_mono("left_mono.wav", "right_mono.wav", "stereo_output.mp3")
    print("Stereo creation example requires mono input files")

    print("\nAudio mixing examples completed!")
    print("Output files: mixed_audio.mp3, merged_audio.mp3, mashup.mp3, with_background.mp3")

if __name__ == "__main__":
    main()
