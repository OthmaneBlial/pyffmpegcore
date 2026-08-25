"""Argparse command registration for the public CLI contract."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__

ROOT_HELP_EPILOG = """Examples:
  pyffmpegcore doctor
  pyffmpegcore probe --input sample.mp4 --json
  pyffmpegcore convert --input clip.webm --output clip.mp4 --video-codec libx264 --audio-codec aac
  pyffmpegcore compress --input input.mp4 --output smaller.mp4 --crf 28
  pyffmpegcore extract-audio --input video.mp4 --output soundtrack.mp3
  pyffmpegcore subtitles burn --video input.mp4 --subtitle captions.srt --output burned.mp4
  pyffmpegcore completion bash

Run `pyffmpegcore COMMAND --help` for command-specific flags.
See CLI_HELP.md for task-based copy-paste examples.
"""


def add_global_arguments(
    parser: argparse.ArgumentParser,
    *,
    suppress_defaults: bool = False,
) -> None:
    """
    Add global CLI arguments shared by the root parser and future subcommands.
    """
    bool_default = argparse.SUPPRESS if suppress_defaults else False
    ffmpeg_default = argparse.SUPPRESS if suppress_defaults else "ffmpeg"
    ffprobe_default = argparse.SUPPRESS if suppress_defaults else "ffprobe"
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "--verbose",
        action="store_true",
        default=bool_default,
        help="Show more detailed command output.",
    )
    verbosity.add_argument(
        "--quiet",
        action="store_true",
        default=bool_default,
        help="Reduce command output to essentials.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=bool_default,
        help="Allow overwriting existing output files or directories.",
    )
    preview = parser.add_mutually_exclusive_group()
    preview.add_argument(
        "--dry-run",
        action="store_true",
        default=bool_default,
        help="Preflight and print the exact plan without writing files.",
    )
    preview.add_argument(
        "--explain",
        action="store_true",
        default=bool_default,
        help="Explain streams, operations, trade-offs, and the exact plan without writing files.",
    )
    parser.add_argument(
        "--plan-json",
        action="store_true",
        default=bool_default,
        help="Print --dry-run or --explain as versioned JSON.",
    )
    parser.add_argument(
        "--result-json",
        action="store_true",
        default=bool_default,
        help="Print the writing command's versioned plan, preflight, and result as JSON.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=argparse.SUPPRESS if suppress_defaults else None,
        metavar="SECONDS",
        help="Stop a writing command after this positive number of seconds.",
    )
    parser.add_argument(
        "--temp-files",
        choices=("clean", "keep-on-error", "keep"),
        default=argparse.SUPPRESS if suppress_defaults else "clean",
        help="Clean temporary files, retain them on error, or always retain them.",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        default=argparse.SUPPRESS if suppress_defaults else None,
        metavar="FILE",
        help="Write a privacy-redacted versioned receipt for an executed media job.",
    )
    parser.add_argument(
        "--hash-content",
        action="store_true",
        default=bool_default,
        help="Opt in to SHA-256 input/output hashes in --receipt.",
    )
    parser.add_argument(
        "--ffmpeg-path",
        default=ffmpeg_default,
        help="Path to the ffmpeg executable. Defaults to ffmpeg.",
    )
    parser.add_argument(
        "--ffprobe-path",
        default=ffprobe_default,
        help="Path to the ffprobe executable. Defaults to ffprobe.",
    )


def build_global_parent(*, suppress_defaults: bool = False) -> argparse.ArgumentParser:
    """
    Build the shared parent parser used by the root parser and subcommands.
    """
    parent = argparse.ArgumentParser(add_help=False)
    add_global_arguments(parent, suppress_defaults=suppress_defaults)
    return parent


def build_parser() -> argparse.ArgumentParser:
    """
    Build the top-level CLI parser.
    """
    root_parent = build_global_parent()
    common_parent = build_global_parent(suppress_defaults=True)
    parser = argparse.ArgumentParser(
        prog="pyffmpegcore",
        parents=[root_parent],
        description=(
            "PyFFmpegCore CLI. A task-focused terminal interface for the verified media workflows in this repository."
        ),
        epilog=ROOT_HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    doctor_parser = subparsers.add_parser(
        "doctor",
        parents=[common_parent],
        help="Show FFmpeg, FFprobe, and environment diagnostics.",
        description="Show FFmpeg, FFprobe, and environment diagnostics.",
    )
    doctor_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the diagnostics as JSON.",
    )
    doctor_parser.set_defaults(handler_name="handle_doctor")

    smoke_parser = subparsers.add_parser(
        "smoke-test",
        parents=[common_parent],
        help="Generate local synthetic media and verify a complete workflow.",
        description=(
            "Generate a tiny local media file, extract a thumbnail, probe both "
            "artifacts, and clean up unless --keep-dir is provided."
        ),
    )
    smoke_parser.add_argument(
        "--keep-dir",
        type=Path,
        help="Keep generated artifacts in this directory instead of using a temporary directory.",
    )
    smoke_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the smoke-test result as JSON.",
    )
    smoke_parser.set_defaults(handler_name="handle_smoke_test")

    completion_parser = subparsers.add_parser(
        "completion",
        parents=[common_parent],
        help="Print a shell completion script for bash, zsh, or PowerShell.",
        description="Print a shell completion script for bash, zsh, or PowerShell.",
    )
    completion_parser.add_argument(
        "shell",
        choices=["bash", "zsh", "powershell"],
        help="Shell name to generate completion for.",
    )
    completion_parser.set_defaults(handler_name="handle_completion")

    profile_parser = subparsers.add_parser(
        "profile",
        parents=[common_parent],
        help="List, explain, or validate versioned workflow profiles.",
        description="Inspect built-in profiles or validate a strict local JSON/TOML profile.",
    )
    profile_subparsers = profile_parser.add_subparsers(dest="profile_command", metavar="COMMAND")

    profile_list_parser = profile_subparsers.add_parser(
        "list",
        parents=[common_parent],
        help="List built-in workflow profiles.",
    )
    profile_list_parser.add_argument("--json", action="store_true", help="Print profiles as JSON.")
    profile_list_parser.set_defaults(handler_name="handle_profile_list")

    profile_show_parser = profile_subparsers.add_parser(
        "show",
        parents=[common_parent],
        help="Explain one built-in profile.",
    )
    profile_show_parser.add_argument("name", help="Profile name, for example web/mp4-compatible.")
    profile_show_parser.add_argument("--json", action="store_true", help="Print the profile as JSON.")
    profile_show_parser.set_defaults(handler_name="handle_profile_show")

    profile_validate_parser = profile_subparsers.add_parser(
        "validate",
        parents=[common_parent],
        help="Validate a local versioned JSON or TOML profile.",
    )
    profile_validate_parser.add_argument("path", type=Path, help="Path to a .json or .toml profile.")
    profile_validate_parser.add_argument("--json", action="store_true", help="Print the validated profile as JSON.")
    profile_validate_parser.set_defaults(handler_name="handle_profile_validate")

    receipt_parser = subparsers.add_parser(
        "receipt",
        parents=[common_parent],
        help="Validate a run receipt or build a private bug-report bundle.",
        description="Validate a run receipt or build a private bug-report bundle.",
    )
    receipt_subparsers = receipt_parser.add_subparsers(dest="receipt_command", metavar="COMMAND")

    receipt_validate_parser = receipt_subparsers.add_parser(
        "validate",
        parents=[common_parent],
        help="Validate a versioned receipt without accessing its media.",
    )
    receipt_validate_parser.add_argument("path", type=Path, help="Path to a receipt JSON file.")
    receipt_validate_parser.add_argument("--json", action="store_true", help="Print validation facts as JSON.")
    receipt_validate_parser.set_defaults(handler_name="handle_receipt_validate")

    receipt_bug_parser = receipt_subparsers.add_parser(
        "bug-report",
        parents=[common_parent],
        help="Combine a redacted receipt with current doctor facts.",
    )
    receipt_bug_parser.add_argument("path", type=Path, help="Path to a validated receipt JSON file.")
    receipt_bug_parser.add_argument("--output", type=Path, help="Write the JSON bundle instead of stdout.")
    receipt_bug_parser.set_defaults(handler_name="handle_receipt_bug_report")

    receipt_migrate_parser = receipt_subparsers.add_parser(
        "migrate",
        parents=[common_parent],
        help="Validate, redact again, and canonicalize a receipt schema.",
    )
    receipt_migrate_parser.add_argument("path", type=Path, help="Path to the source receipt JSON file.")
    receipt_migrate_parser.add_argument("--output", type=Path, help="Write the canonical receipt instead of stdout.")
    receipt_migrate_parser.add_argument(
        "--target-version", default="1.0", help="Target receipt schema. Defaults to %(default)s."
    )
    receipt_migrate_parser.set_defaults(handler_name="handle_receipt_migrate")

    probe_parser = subparsers.add_parser(
        "probe",
        parents=[common_parent],
        help="Inspect a media file and print simplified metadata.",
        description="Inspect a media file and print simplified metadata.",
    )
    probe_parser.add_argument(
        "--input",
        required=True,
        help="Path to the media file to inspect.",
    )
    probe_parser.add_argument(
        "--json",
        action="store_true",
        help="Print simplified metadata as JSON.",
    )
    probe_parser.set_defaults(handler_name="handle_probe")

    convert_parser = subparsers.add_parser(
        "convert",
        parents=[common_parent],
        help="Convert a media file into a new format.",
        description="Convert a media file into a new format.",
    )
    convert_parser.add_argument(
        "--input",
        required=True,
        help="Path to the input media file.",
    )
    convert_parser.add_argument(
        "--output",
        required=True,
        help="Path to the converted output file.",
    )
    convert_parser.add_argument(
        "--audio-only",
        action="store_true",
        help="Drop video and keep only the audio stream.",
    )
    convert_parser.add_argument(
        "--video-codec",
        help="Video codec to use, for example libx264.",
    )
    convert_parser.add_argument(
        "--audio-codec",
        help="Audio codec to use, for example aac.",
    )
    convert_parser.add_argument(
        "--video-bitrate",
        help="Video bitrate, for example 2500k.",
    )
    convert_parser.add_argument(
        "--audio-bitrate",
        help="Audio bitrate, for example 192k.",
    )
    convert_parser.add_argument(
        "--pix-fmt",
        help="Pixel format for video output, for example yuv420p.",
    )
    convert_parser.add_argument(
        "--threads",
        type=int,
        help="Number of FFmpeg worker threads to use.",
    )
    convert_parser.add_argument(
        "--hwaccel",
        help="Optional FFmpeg hardware-acceleration method; failures do not silently fall back.",
    )
    convert_parser.set_defaults(handler_name="handle_planned_command")

    compress_parser = subparsers.add_parser(
        "compress",
        parents=[common_parent],
        help="Compress a video file with CRF or target-size settings.",
        description="Compress a video file with CRF or target-size settings.",
    )
    compress_parser.add_argument(
        "--input",
        required=True,
        help="Path to the input video file.",
    )
    compress_parser.add_argument(
        "--output",
        required=True,
        help="Path to the compressed output file.",
    )
    compress_parser.add_argument(
        "--crf",
        type=int,
        default=23,
        help="CRF quality level for single-pass compression. Defaults to %(default)s.",
    )
    target_size_group = compress_parser.add_mutually_exclusive_group()
    target_size_group.add_argument(
        "--target-size-kb",
        type=int,
        help="Target output size in kilobytes for two-pass compression.",
    )
    target_size_group.add_argument(
        "--target-size",
        help="Target output size with an explicit unit, for example 25MB or 25MiB.",
    )
    pass_group = compress_parser.add_mutually_exclusive_group()
    pass_group.add_argument(
        "--two-pass",
        dest="two_pass",
        action="store_true",
        help="Force two-pass compression when target size is set.",
    )
    pass_group.add_argument(
        "--single-pass",
        dest="two_pass",
        action="store_false",
        help="Use single-pass compression even when a target size is set.",
    )
    compress_parser.set_defaults(two_pass=True)
    compress_parser.add_argument(
        "--video-codec",
        help="Video codec to use, for example libx264.",
    )
    compress_parser.add_argument(
        "--audio-codec",
        help="Audio codec to use, for example aac.",
    )
    compress_parser.add_argument(
        "--video-bitrate",
        help="Video bitrate override, for example 1500k.",
    )
    compress_parser.add_argument(
        "--audio-bitrate",
        help="Audio bitrate override, for example 128k.",
    )
    compress_parser.add_argument(
        "--preset",
        help="Encoding preset, for example medium or fast.",
    )
    compress_parser.add_argument(
        "--threads",
        type=int,
        help="Number of FFmpeg worker threads to use.",
    )
    compress_parser.add_argument(
        "--min-video-bitrate",
        default="100k",
        help="Two-pass quality floor in bits/s, for example 100k. Defaults to %(default)s.",
    )
    compress_parser.add_argument(
        "--container-overhead-percent",
        type=float,
        default=1.0,
        help="Reserved target-size percentage for container overhead. Defaults to %(default)s.",
    )
    compress_parser.set_defaults(handler_name="handle_planned_command")

    extract_audio_parser = subparsers.add_parser(
        "extract-audio",
        parents=[common_parent],
        help="Extract the audio stream from a media file.",
        description="Extract the audio stream from a media file.",
    )
    extract_audio_parser.add_argument(
        "--input",
        required=True,
        help="Path to the input media file.",
    )
    extract_audio_parser.add_argument(
        "--output",
        required=True,
        help="Path to the audio output file.",
    )
    extract_audio_parser.add_argument(
        "--audio-codec",
        help="Audio codec override, for example libmp3lame or pcm_s16le.",
    )
    extract_audio_parser.add_argument(
        "--audio-bitrate",
        help="Audio bitrate override, for example 192k.",
    )
    extract_audio_parser.add_argument(
        "--sample-rate",
        type=int,
        help="Sample rate override in Hz.",
    )
    extract_audio_parser.add_argument(
        "--channels",
        type=int,
        help="Channel count override.",
    )
    extract_audio_parser.add_argument(
        "--threads",
        type=int,
        help="Number of FFmpeg worker threads to use.",
    )
    extract_audio_parser.set_defaults(handler_name="handle_planned_command")

    thumbnail_parser = subparsers.add_parser(
        "thumbnail",
        parents=[common_parent],
        help="Extract a thumbnail image from a video file.",
        description="Extract a thumbnail image from a video file.",
    )
    thumbnail_parser.add_argument(
        "--input",
        required=True,
        help="Path to the input video file.",
    )
    thumbnail_parser.add_argument(
        "--output",
        required=True,
        help="Path to the thumbnail image output.",
    )
    thumbnail_parser.add_argument(
        "--timestamp",
        default="00:00:01",
        help="Timestamp in HH:MM:SS or HH:MM:SS.ms format. Defaults to %(default)s.",
    )
    thumbnail_parser.add_argument(
        "--width",
        type=int,
        default=320,
        help="Thumbnail width in pixels. Defaults to %(default)s.",
    )
    thumbnail_parser.add_argument(
        "--height",
        type=int,
        help="Optional thumbnail height in pixels.",
    )
    thumbnail_parser.add_argument(
        "--quality",
        type=int,
        default=2,
        help="JPEG quality from 1 to 31. Lower is better quality. Defaults to %(default)s.",
    )
    thumbnail_parser.set_defaults(handler_name="handle_planned_command")

    waveform_parser = subparsers.add_parser(
        "waveform",
        parents=[common_parent],
        help="Generate a waveform image from audio or video-with-audio.",
        description="Generate a waveform image from audio or video-with-audio.",
    )
    waveform_parser.add_argument(
        "--input",
        required=True,
        help="Path to the input audio or video file.",
    )
    waveform_parser.add_argument(
        "--output",
        required=True,
        help="Path to the waveform image output.",
    )
    waveform_parser.add_argument(
        "--width",
        type=int,
        default=800,
        help="Waveform width in pixels. Defaults to %(default)s.",
    )
    waveform_parser.add_argument(
        "--height",
        type=int,
        default=200,
        help="Waveform height in pixels. Defaults to %(default)s.",
    )
    waveform_parser.add_argument(
        "--colors",
        default="white",
        help="Waveform color definition. Defaults to %(default)s.",
    )
    waveform_parser.set_defaults(handler_name="handle_planned_command")

    speed_parser = subparsers.add_parser(
        "speed",
        parents=[common_parent],
        help="Change playback speed for video or audio media.",
        description="Change playback speed for video or audio media.",
    )
    speed_subparsers = speed_parser.add_subparsers(
        dest="speed_command",
        metavar="SPEED_COMMAND",
        required=True,
    )

    speed_video_parser = speed_subparsers.add_parser(
        "video",
        parents=[common_parent],
        help="Change playback speed for a video file.",
        description="Change playback speed for a video file.",
    )
    speed_video_parser.add_argument("--input", required=True, help="Path to the input video file.")
    speed_video_parser.add_argument("--output", required=True, help="Path to the output video file.")
    speed_video_parser.add_argument(
        "--factor",
        required=True,
        type=float,
        help="Playback speed factor, for example 1.5 or 0.5.",
    )
    speed_video_parser.add_argument(
        "--no-pitch-preserve",
        action="store_true",
        help="Do not preserve audio pitch when changing playback speed.",
    )
    speed_video_parser.set_defaults(handler_name="handle_planned_command")

    speed_audio_parser = speed_subparsers.add_parser(
        "audio",
        parents=[common_parent],
        help="Change playback speed for an audio file.",
        description="Change playback speed for an audio file.",
    )
    speed_audio_parser.add_argument("--input", required=True, help="Path to the input audio file.")
    speed_audio_parser.add_argument("--output", required=True, help="Path to the output audio file.")
    speed_audio_parser.add_argument(
        "--factor",
        required=True,
        type=float,
        help="Playback speed factor, for example 1.25 or 0.8.",
    )
    speed_audio_parser.add_argument(
        "--no-pitch-preserve",
        action="store_true",
        help="Do not preserve pitch when changing playback speed.",
    )
    speed_audio_parser.set_defaults(handler_name="handle_planned_command")

    concat_parser = subparsers.add_parser(
        "concat",
        parents=[common_parent],
        help="Join multiple video clips into one output.",
        description="Join multiple video clips into one output.",
    )
    concat_parser.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="Input clip paths in the order they should appear in the output.",
    )
    concat_parser.add_argument(
        "--output",
        required=True,
        help="Path to the concatenated output video.",
    )
    concat_parser.add_argument(
        "--mode",
        choices=["copy", "reencode"],
        default="copy",
        help="Use fast stream-copy concat or a safer re-encode path. Defaults to %(default)s.",
    )
    concat_parser.add_argument(
        "--video-codec",
        default="libx264",
        help="Video codec for re-encode mode. Defaults to %(default)s.",
    )
    concat_parser.add_argument(
        "--audio-codec",
        default="aac",
        help="Audio codec for re-encode mode. Defaults to %(default)s.",
    )
    concat_parser.set_defaults(handler_name="handle_planned_command")

    subtitles_parser = subparsers.add_parser(
        "subtitles",
        parents=[common_parent],
        help="Add, extract, or burn subtitle tracks.",
        description="Add, extract, or burn subtitle tracks.",
    )
    subtitles_subparsers = subtitles_parser.add_subparsers(
        dest="subtitles_command",
        metavar="SUBTITLES_COMMAND",
        required=True,
    )

    subtitles_add_parser = subtitles_subparsers.add_parser(
        "add",
        parents=[common_parent],
        help="Add an external subtitle file as a selectable track.",
        description="Add an external subtitle file as a selectable track.",
    )
    subtitles_add_parser.add_argument("--video", required=True, help="Path to the input video file.")
    subtitles_add_parser.add_argument("--subtitle", required=True, help="Path to the subtitle file.")
    subtitles_add_parser.add_argument("--output", required=True, help="Path to the output video file.")
    subtitles_add_parser.add_argument(
        "--language",
        default="eng",
        help="Subtitle language code. Defaults to %(default)s.",
    )
    subtitles_add_parser.set_defaults(handler_name="handle_planned_command")

    subtitles_extract_parser = subtitles_subparsers.add_parser(
        "extract",
        parents=[common_parent],
        help="Extract a subtitle stream from a video file.",
        description="Extract a subtitle stream from a video file.",
    )
    subtitles_extract_parser.add_argument("--video", required=True, help="Path to the input video file.")
    subtitles_extract_parser.add_argument("--output", required=True, help="Path to the extracted subtitle file.")
    subtitles_extract_parser.add_argument(
        "--stream-index",
        type=int,
        default=0,
        help="Zero-based subtitle stream index. Defaults to %(default)s.",
    )
    subtitles_extract_parser.set_defaults(handler_name="handle_planned_command")

    subtitles_burn_parser = subtitles_subparsers.add_parser(
        "burn",
        parents=[common_parent],
        help="Burn subtitle text permanently into the video image.",
        description="Burn subtitle text permanently into the video image.",
    )
    subtitles_burn_parser.add_argument("--video", required=True, help="Path to the input video file.")
    subtitles_burn_parser.add_argument("--subtitle", required=True, help="Path to the subtitle file.")
    subtitles_burn_parser.add_argument("--output", required=True, help="Path to the output video file.")
    subtitles_burn_parser.add_argument(
        "--font-size",
        type=int,
        default=24,
        help="Subtitle font size. Defaults to %(default)s.",
    )
    subtitles_burn_parser.add_argument(
        "--font-color",
        default="&HFFFFFF",
        help="ASS/FFmpeg subtitle color value. Defaults to %(default)s.",
    )
    subtitles_burn_parser.set_defaults(handler_name="handle_planned_command")

    mix_audio_parser = subparsers.add_parser(
        "mix-audio",
        parents=[common_parent],
        help="Mix, concatenate, mash up, or layer multiple audio sources.",
        description="Mix, concatenate, mash up, or layer multiple audio sources.",
    )
    mix_audio_subparsers = mix_audio_parser.add_subparsers(
        dest="mix_audio_command",
        metavar="MIX_AUDIO_COMMAND",
        required=True,
    )

    mix_audio_mix_parser = mix_audio_subparsers.add_parser(
        "mix",
        parents=[common_parent],
        help="Mix multiple audio sources together.",
        description="Mix multiple audio sources together.",
    )
    mix_audio_mix_parser.add_argument("--inputs", nargs="+", required=True, help="Audio input paths.")
    mix_audio_mix_parser.add_argument("--output", required=True, help="Mixed audio output path.")
    mix_audio_mix_parser.add_argument(
        "--volumes",
        nargs="*",
        type=float,
        help="Optional per-input volume multipliers.",
    )
    mix_audio_mix_parser.set_defaults(handler_name="handle_planned_command")

    mix_audio_concat_parser = mix_audio_subparsers.add_parser(
        "concat",
        parents=[common_parent],
        help="Concatenate audio files one after another.",
        description="Concatenate audio files one after another.",
    )
    mix_audio_concat_parser.add_argument("--inputs", nargs="+", required=True, help="Audio input paths.")
    mix_audio_concat_parser.add_argument("--output", required=True, help="Merged audio output path.")
    mix_audio_concat_parser.set_defaults(handler_name="handle_planned_command")

    mix_audio_mashup_parser = mix_audio_subparsers.add_parser(
        "mashup",
        parents=[common_parent],
        help="Crossfade multiple audio files into a mashup.",
        description="Crossfade multiple audio files into a mashup.",
    )
    mix_audio_mashup_parser.add_argument("--inputs", nargs="+", required=True, help="Audio input paths.")
    mix_audio_mashup_parser.add_argument("--output", required=True, help="Mashup audio output path.")
    mix_audio_mashup_parser.add_argument(
        "--crossfade-duration",
        type=float,
        default=2.0,
        help="Crossfade duration in seconds. Defaults to %(default)s.",
    )
    mix_audio_mashup_parser.set_defaults(handler_name="handle_planned_command")

    mix_audio_background_parser = mix_audio_subparsers.add_parser(
        "background",
        parents=[common_parent],
        help="Layer background music under a main audio track.",
        description="Layer background music under a main audio track.",
    )
    mix_audio_background_parser.add_argument("--main-input", required=True, help="Main audio source.")
    mix_audio_background_parser.add_argument("--background-input", required=True, help="Background audio source.")
    mix_audio_background_parser.add_argument("--output", required=True, help="Mixed audio output path.")
    mix_audio_background_parser.add_argument(
        "--bg-volume",
        type=float,
        default=0.3,
        help="Background volume multiplier. Defaults to %(default)s.",
    )
    mix_audio_background_parser.set_defaults(handler_name="handle_planned_command")

    normalize_audio_parser = subparsers.add_parser(
        "normalize-audio",
        parents=[common_parent],
        help="Normalize or master an audio file.",
        description="Normalize or master an audio file.",
    )
    normalize_audio_parser.add_argument("--input", required=True, help="Input audio or video file.")
    normalize_audio_parser.add_argument("--output", required=True, help="Output audio file.")
    normalize_audio_parser.add_argument(
        "--method",
        choices=["loudnorm", "master"],
        default="loudnorm",
        help="Normalization method. Defaults to %(default)s.",
    )
    normalize_audio_parser.add_argument(
        "--target-i",
        type=float,
        default=-16.0,
        help="Target integrated loudness in LUFS for loudnorm mode.",
    )
    normalize_audio_parser.add_argument(
        "--target-tp",
        type=float,
        default=-1.5,
        help="Target true peak in dBTP for loudnorm mode.",
    )
    normalize_audio_parser.add_argument(
        "--target-lra",
        type=float,
        default=11.0,
        help="Target loudness range in LU for loudnorm mode.",
    )
    normalize_audio_parser.set_defaults(handler_name="handle_planned_command")

    images_parser = subparsers.add_parser(
        "images",
        parents=[common_parent],
        help="Batch-convert or optimize image directories.",
        description="Batch-convert or optimize image directories.",
    )
    images_subparsers = images_parser.add_subparsers(
        dest="images_command",
        metavar="IMAGES_COMMAND",
        required=True,
    )

    images_convert_parser = images_subparsers.add_parser(
        "convert",
        parents=[common_parent],
        help="Convert a directory of images into another format.",
        description="Convert a directory of images into another format.",
    )
    images_convert_parser.add_argument("--input-dir", required=True, help="Directory containing input images.")
    images_convert_parser.add_argument("--output-dir", required=True, help="Directory for converted outputs.")
    images_convert_parser.add_argument(
        "--format",
        default="jpg",
        help="Output format such as jpg, png, or webp. Defaults to %(default)s.",
    )
    images_convert_parser.add_argument(
        "--quality",
        type=int,
        default=85,
        help="Output quality from 1 to 100. Defaults to %(default)s.",
    )
    images_convert_parser.add_argument(
        "--resize",
        nargs=2,
        type=int,
        metavar=("WIDTH", "HEIGHT"),
        help="Optional resize dimensions applied to every output image.",
    )
    images_convert_parser.set_defaults(handler_name="handle_planned_command")

    images_optimize_parser = images_subparsers.add_parser(
        "optimize",
        parents=[common_parent],
        help="Resize and convert images into web-friendly JPEG outputs.",
        description="Resize and convert images into web-friendly JPEG outputs.",
    )
    images_optimize_parser.add_argument("--input-dir", required=True, help="Directory containing input images.")
    images_optimize_parser.add_argument("--output-dir", required=True, help="Directory for optimized outputs.")
    images_optimize_parser.add_argument(
        "--max-width",
        type=int,
        default=1920,
        help="Maximum image width. Defaults to %(default)s.",
    )
    images_optimize_parser.add_argument(
        "--max-height",
        type=int,
        default=1080,
        help="Maximum image height. Defaults to %(default)s.",
    )
    images_optimize_parser.add_argument(
        "--quality",
        type=int,
        default=85,
        help="JPEG quality from 1 to 100. Defaults to %(default)s.",
    )
    images_optimize_parser.set_defaults(handler_name="handle_planned_command")

    images_webp_parser = images_subparsers.add_parser(
        "webp",
        parents=[common_parent],
        help="Convert a directory of images into WebP outputs.",
        description="Convert a directory of images into WebP outputs.",
    )
    images_webp_parser.add_argument("--input-dir", required=True, help="Directory containing input images.")
    images_webp_parser.add_argument("--output-dir", required=True, help="Directory for WebP outputs.")
    images_webp_parser.add_argument(
        "--quality",
        type=int,
        default=80,
        help="WebP quality from 1 to 100. Defaults to %(default)s.",
    )
    images_webp_parser.set_defaults(handler_name="handle_planned_command")

    return parser
