"""
Command-line entrypoint for PyFFmpegCore.
"""

from __future__ import annotations

import argparse
import json
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .capabilities import CapabilityInventory
from .cli_execution import CLIExecutionBundle, execute_prepared_cli_job, prepare_cli_job
from .cli_planning import build_cli_plan
from .domain import JobResult, ProgressEvent
from .errors import ValidationError
from .preflight import PreflightEngine
from .presentation import render_plan_json, render_plan_text
from .probe import FFprobeRunner
from .profiles import Profile, ProfileRegistry
from .runner import FFmpegRunner

EXIT_OK = 0
EXIT_ENVIRONMENT_ERROR = 3
EXIT_USAGE_ERROR = 2
EXIT_VALIDATION_ERROR = 4
EXIT_RUNTIME_ERROR = 5
EXIT_PARTIAL_SUCCESS = 6

WRITING_COMMANDS = frozenset(
    {
        "convert",
        "compress",
        "extract-audio",
        "thumbnail",
        "waveform",
        "speed",
        "concat",
        "subtitles",
        "mix-audio",
        "normalize-audio",
        "images",
    }
)

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


class CLIError(RuntimeError):
    """
    User-facing CLI error with a stable exit code.
    """

    def __init__(self, message: str, exit_code: int = EXIT_VALIDATION_ERROR):
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class CLIContext:
    """
    Shared execution context derived from parsed CLI arguments.
    """

    verbose: bool = False
    quiet: bool = False
    force: bool = False
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"


class CLIProgressPrinter:
    """
    Lightweight terminal progress printer for FFmpeg jobs.
    """

    def __init__(self, total_duration: float | None = None):
        self.total_duration = total_duration
        self.seen_progress = False

    def __call__(self, progress: dict[str, Any]) -> None:
        if progress.get("status") == "end":
            if self.seen_progress:
                print("\rProgress: 100% complete", file=sys.stderr)
            return

        time_seconds = progress.get("time_seconds")
        if time_seconds is not None and self.total_duration:
            self.seen_progress = True
            percentage = min(100.0, (time_seconds / self.total_duration) * 100.0)
            print(
                f"\rProgress: {percentage:5.1f}% ({time_seconds:0.2f}s)",
                end="",
                file=sys.stderr,
                flush=True,
            )
            return

        frame = progress.get("frame")
        if frame is not None:
            self.seen_progress = True
            print(
                f"\rFrame: {frame}",
                end="",
                file=sys.stderr,
                flush=True,
            )


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
    doctor_parser.set_defaults(handler=handle_doctor)

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
    smoke_parser.set_defaults(handler=handle_smoke_test)

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
    completion_parser.set_defaults(handler=handle_completion)

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
    profile_list_parser.set_defaults(handler=handle_profile_list)

    profile_show_parser = profile_subparsers.add_parser(
        "show",
        parents=[common_parent],
        help="Explain one built-in profile.",
    )
    profile_show_parser.add_argument("name", help="Profile name, for example web/mp4-compatible.")
    profile_show_parser.add_argument("--json", action="store_true", help="Print the profile as JSON.")
    profile_show_parser.set_defaults(handler=handle_profile_show)

    profile_validate_parser = profile_subparsers.add_parser(
        "validate",
        parents=[common_parent],
        help="Validate a local versioned JSON or TOML profile.",
    )
    profile_validate_parser.add_argument("path", type=Path, help="Path to a .json or .toml profile.")
    profile_validate_parser.add_argument("--json", action="store_true", help="Print the validated profile as JSON.")
    profile_validate_parser.set_defaults(handler=handle_profile_validate)

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
    probe_parser.set_defaults(handler=handle_probe)

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
    convert_parser.set_defaults(handler=handle_planned_command)

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
    compress_parser.set_defaults(handler=handle_planned_command)

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
    extract_audio_parser.set_defaults(handler=handle_planned_command)

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
    thumbnail_parser.set_defaults(handler=handle_planned_command)

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
    waveform_parser.set_defaults(handler=handle_planned_command)

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
    speed_video_parser.set_defaults(handler=handle_planned_command)

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
    speed_audio_parser.set_defaults(handler=handle_planned_command)

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
    concat_parser.set_defaults(handler=handle_planned_command)

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
    subtitles_add_parser.set_defaults(handler=handle_planned_command)

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
    subtitles_extract_parser.set_defaults(handler=handle_planned_command)

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
    subtitles_burn_parser.set_defaults(handler=handle_planned_command)

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
    mix_audio_mix_parser.set_defaults(handler=handle_planned_command)

    mix_audio_concat_parser = mix_audio_subparsers.add_parser(
        "concat",
        parents=[common_parent],
        help="Concatenate audio files one after another.",
        description="Concatenate audio files one after another.",
    )
    mix_audio_concat_parser.add_argument("--inputs", nargs="+", required=True, help="Audio input paths.")
    mix_audio_concat_parser.add_argument("--output", required=True, help="Merged audio output path.")
    mix_audio_concat_parser.set_defaults(handler=handle_planned_command)

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
    mix_audio_mashup_parser.set_defaults(handler=handle_planned_command)

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
    mix_audio_background_parser.set_defaults(handler=handle_planned_command)

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
    normalize_audio_parser.set_defaults(handler=handle_planned_command)

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
    images_convert_parser.set_defaults(handler=handle_planned_command)

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
    images_optimize_parser.set_defaults(handler=handle_planned_command)

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
    images_webp_parser.set_defaults(handler=handle_planned_command)

    return parser


def collect_completion_metadata(
    parser: argparse.ArgumentParser,
    path: tuple[str, ...] = (),
) -> dict[tuple[str, ...], dict[str, list[str]]]:
    """
    Collect subcommand and option metadata from an argparse tree.
    """
    metadata: dict[tuple[str, ...], dict[str, list[str]]] = {}
    options: list[str] = []
    subcommand_parsers: dict[str, argparse.ArgumentParser] = {}

    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, subparser in action.choices.items():
                subcommand_parsers[name] = subparser
            continue
        if action.option_strings and action.help != argparse.SUPPRESS:
            options.extend(action.option_strings)

    metadata[path] = {
        "options": sorted(dict.fromkeys(options)),
        "subcommands": sorted(subcommand_parsers),
    }

    for name, subparser in subcommand_parsers.items():
        metadata.update(collect_completion_metadata(subparser, path + (name,)))

    return metadata


def completion_key(path: tuple[str, ...]) -> str:
    """
    Render a shell-safe key for a parser path.
    """
    return "root" if not path else "__".join(path)


def powershell_quote(value: str) -> str:
    """
    Quote a literal string for PowerShell array output.
    """
    return "'" + value.replace("'", "''") + "'"


def render_bash_completion(program_name: str, metadata: dict[tuple[str, ...], dict[str, list[str]]]) -> str:
    """
    Render a bash completion function from parser metadata.
    """
    lines = [
        f"_{program_name}_completion() {{",
        "    local cur key",
        "    COMPREPLY=()",
        '    cur="${COMP_WORDS[COMP_CWORD]}"',
        "    key=root",
        "    for ((i=1; i<COMP_CWORD; i++)); do",
        '        case "$key:${COMP_WORDS[i]}" in',
    ]

    for path, node in metadata.items():
        key = completion_key(path)
        for subcommand in node["subcommands"]:
            next_key = completion_key(path + (subcommand,))
            lines.append(f"            {key}:{subcommand}) key={next_key} ;;")

    lines.extend(
        [
            "        esac",
            "    done",
            '    case "$key" in',
        ]
    )

    for path, node in metadata.items():
        key = completion_key(path)
        candidates = " ".join(node["subcommands"] + node["options"])
        lines.append(f'        {key}) COMPREPLY=( $(compgen -W {shlex.quote(candidates)} -- "$cur") ) ;;')

    lines.extend(
        [
            "    esac",
            "}",
            f"complete -F _{program_name}_completion {program_name}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_zsh_completion(program_name: str, metadata: dict[tuple[str, ...], dict[str, list[str]]]) -> str:
    """
    Render a zsh completion function from parser metadata.
    """
    lines = [
        f"#compdef {program_name}",
        "",
        f"_{program_name}() {{",
        '  local key="root"',
        "  local -a candidates",
        "  local word",
        "  for (( i=2; i<CURRENT; i++ )); do",
        '    word="${words[i]}"',
        '    case "$key:$word" in',
    ]

    for path, node in metadata.items():
        key = completion_key(path)
        for subcommand in node["subcommands"]:
            next_key = completion_key(path + (subcommand,))
            lines.append(f'      {key}:{subcommand}) key="{next_key}" ;;')

    lines.extend(
        [
            "    esac",
            "  done",
            '  case "$key" in',
        ]
    )

    for path, node in metadata.items():
        key = completion_key(path)
        candidates = " ".join(shlex.quote(word) for word in (node["subcommands"] + node["options"]))
        lines.append(f"    {key}) candidates=({candidates}) ;;")

    lines.extend(
        [
            "  esac",
            "  _describe 'pyffmpegcore arguments' candidates",
            "}",
            "",
            f"compdef _{program_name} {program_name}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_powershell_completion(
    program_name: str,
    metadata: dict[tuple[str, ...], dict[str, list[str]]],
) -> str:
    """
    Render a PowerShell argument completer from parser metadata.
    """
    lines = [
        f"Register-ArgumentCompleter -Native -CommandName {program_name} -ScriptBlock {{",
        "    param($wordToComplete, $commandAst, $cursorPosition)",
        "    $tokens = @($commandAst.CommandElements | Select-Object -Skip 1 | ForEach-Object { $_.Extent.Text })",
        "    if ($tokens.Count -eq 0) {",
        "        $previousTokens = @()",
        "    } elseif ($tokens.Count -eq 1) {",
        "        $previousTokens = @()",
        "    } else {",
        "        $previousTokens = $tokens[0..($tokens.Count - 2)]",
        "    }",
        '    $key = "root"',
        "    foreach ($token in $previousTokens) {",
        '        switch ("$key:$token") {',
    ]

    for path, node in metadata.items():
        key = completion_key(path)
        for subcommand in node["subcommands"]:
            next_key = completion_key(path + (subcommand,))
            lines.append(f'            "{key}:{subcommand}" {{ $key = "{next_key}"; continue }}')

    lines.extend(
        [
            "        }",
            "    }",
            "    $candidates = switch ($key) {",
        ]
    )

    for path, node in metadata.items():
        key = completion_key(path)
        candidates = ", ".join(powershell_quote(word) for word in (node["subcommands"] + node["options"]))
        lines.append(f'        "{key}" {{ @({candidates}) }}')

    lines.extend(
        [
            "    }",
            '    $candidates | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {',
            "        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)",
            "    }",
            "}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_completion_script(shell: str) -> str:
    """
    Render the requested shell completion script.
    """
    parser = build_parser()
    metadata = collect_completion_metadata(parser)
    if shell == "bash":
        return render_bash_completion("pyffmpegcore", metadata)
    if shell == "zsh":
        return render_zsh_completion("pyffmpegcore", metadata)
    if shell == "powershell":
        return render_powershell_completion("pyffmpegcore", metadata)
    raise CLIError(f"Unsupported completion shell: {shell}", exit_code=EXIT_USAGE_ERROR)


def handle_completion(args: argparse.Namespace) -> int:
    """
    Print a shell completion script to stdout.
    """
    print(render_completion_script(args.shell), end="")
    return EXIT_OK


def render_profile(ctx: CLIContext, profile: Profile) -> None:
    """Render a profile without hiding its output choices or requirements."""
    echo(ctx, f"{profile.name} v{profile.profile_version}")
    echo(ctx, profile.description)
    echo(ctx, f"Workflow: {profile.workflow}")
    echo(ctx, "Options:")
    for name, value in sorted(profile.options.items()):
        echo(ctx, f"  {name}: {value}")
    echo(ctx, "Required capabilities:")
    for capability in profile.required_capabilities:
        echo(ctx, f"  {capability}")


def handle_profile_list(args: argparse.Namespace) -> int:
    """List every maintained built-in profile."""
    profiles = ProfileRegistry().list()
    if args.json:
        print(json.dumps({"schema_version": "1.0", "profiles": [item.to_dict() for item in profiles]}, indent=2))
        return EXIT_OK
    ctx = build_context(args)
    for profile in profiles:
        echo(ctx, f"{profile.name} v{profile.profile_version} — {profile.description}")
    return EXIT_OK


def handle_profile_show(args: argparse.Namespace) -> int:
    """Show the exact choices made by one built-in profile."""
    try:
        profile = ProfileRegistry().get(args.name)
    except ValueError as exc:
        raise CLIError(str(exc)) from exc
    if args.json:
        print(json.dumps(profile.to_dict(), indent=2))
    else:
        render_profile(build_context(args), profile)
    return EXIT_OK


def handle_profile_validate(args: argparse.Namespace) -> int:
    """Validate a project or user profile without executing a media job."""
    try:
        profile = ProfileRegistry().load_file(args.path)
    except ValueError as exc:
        raise CLIError(str(exc)) from exc
    if args.json:
        print(json.dumps({"valid": True, "profile": profile.to_dict()}, indent=2))
    else:
        echo(build_context(args), f"Valid profile: {profile.name} v{profile.profile_version}")
    return EXIT_OK


def build_context(args: argparse.Namespace) -> CLIContext:
    """
    Build a shared CLI context from parsed arguments.
    """
    return CLIContext(
        verbose=getattr(args, "verbose", False),
        quiet=getattr(args, "quiet", False),
        force=getattr(args, "force", False),
        ffmpeg_path=getattr(args, "ffmpeg_path", "ffmpeg"),
        ffprobe_path=getattr(args, "ffprobe_path", "ffprobe"),
    )


def require_existing_input(path_str: str, option_name: str = "--input") -> Path:
    """
    Validate that a required input path exists.
    """
    if not path_str:
        raise CLIError(f"{option_name} is required.")

    path = Path(path_str)
    if not path.exists():
        raise CLIError(f"Input path does not exist: {path}")

    return path


def require_output_path(path_str: str, option_name: str = "--output") -> Path:
    """
    Validate that a required output path was provided.
    """
    if not path_str:
        raise CLIError(f"{option_name} is required.")

    return Path(path_str)


def prepare_output_path(
    path_str: str,
    force: bool,
    option_name: str = "--output",
) -> Path:
    """
    Validate and prepare a file output path.
    """
    path = require_output_path(path_str, option_name=option_name)
    if path.exists() and not force:
        raise CLIError(
            f"Output already exists: {path}. Re-run with --force to overwrite.",
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def prepare_output_dir(
    path_str: str,
    force: bool,
    option_name: str = "--output-dir",
) -> Path:
    """
    Validate and prepare a directory output path.
    """
    if not path_str:
        raise CLIError(f"{option_name} is required.")

    path = Path(path_str)
    if path.exists() and any(path.iterdir()) and not force:
        raise CLIError(
            f"Output directory is not empty: {path}. Re-run with --force to reuse it.",
        )

    path.mkdir(parents=True, exist_ok=True)
    return path


def echo(ctx: CLIContext, message: str) -> None:
    """
    Print a human-readable message unless quiet mode is enabled.
    """
    if not ctx.quiet:
        print(message)


def echo_verbose(ctx: CLIContext, message: str) -> None:
    """
    Print diagnostic detail to stderr when verbose mode is enabled.
    """
    if ctx.verbose:
        print(f"[verbose] {message}", file=sys.stderr)


def echo_error(message: str) -> None:
    """
    Print a user-facing error message to stderr.
    """
    print(message, file=sys.stderr)


def runtime_error_to_cli_error(exc: RuntimeError) -> CLIError:
    """
    Map runtime errors from FFmpeg/FFprobe helpers into stable CLI categories.
    """
    message = str(exc)
    exit_code = EXIT_ENVIRONMENT_ERROR if "was not found" in message else EXIT_RUNTIME_ERROR
    return CLIError(message, exit_code=exit_code)


def format_bytes(byte_count: int | None) -> str:
    """
    Format byte counts into a compact human-readable string.
    """
    if byte_count is None:
        return "unknown"

    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(byte_count)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024

    return f"{byte_count} B"


def inspect_binary(binary_path: str) -> dict[str, Any]:
    """
    Inspect a binary path for existence and version information.
    """
    is_explicit_path = any(sep in binary_path for sep in ("/", "\\"))
    resolved = (
        str(Path(binary_path).resolve())
        if is_explicit_path and Path(binary_path).exists()
        else shutil.which(binary_path)
    )
    report: dict[str, Any] = {
        "requested": binary_path,
        "resolved": resolved,
        "available": False,
        "version": None,
        "error": None,
    }

    if resolved is None:
        report["error"] = f"Executable not found: {binary_path}"
        return report

    try:
        result = subprocess.run(
            [binary_path, "-version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        report["error"] = str(exc)
        return report

    if result.returncode == 0:
        report["available"] = True
        output_lines = result.stdout.splitlines()
        report["version"] = output_lines[0] if output_lines else ""
        report["configuration"] = next(
            (line.removeprefix("configuration: ") for line in output_lines if line.startswith("configuration: ")),
            None,
        )
        return report

    report["error"] = result.stderr.strip() or "Version probe failed"
    return report


def inspect_ffmpeg_capabilities(binary_path: str) -> dict[str, Any]:
    """Collect a versioned inventory used by doctor and workflow preflight."""
    return CapabilityInventory.inspect(binary_path).to_dict()


def collect_doctor_report(ctx: CLIContext) -> dict[str, Any]:
    """
    Collect environment diagnostics for the CLI.
    """
    ffmpeg = inspect_binary(ctx.ffmpeg_path)
    ffprobe = inspect_binary(ctx.ffprobe_path)
    capabilities = inspect_ffmpeg_capabilities(ctx.ffmpeg_path) if ffmpeg["available"] else None
    return {
        "cli_version": __version__,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
        },
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "capabilities": capabilities,
    }


def render_doctor_report(ctx: CLIContext, report: dict[str, Any]) -> None:
    """
    Print a human-readable diagnostics report.
    """
    platform_info = report["platform"]
    python_info = report["python"]

    echo(ctx, f"PyFFmpegCore CLI {report['cli_version']}")
    echo(ctx, f"Platform: {platform_info['system']} {platform_info['release']} ({platform_info['machine']})")
    echo(ctx, f"Python: {python_info['version']} ({python_info['executable']})")

    for label in ("ffmpeg", "ffprobe"):
        binary_report = report[label]
        if binary_report["available"]:
            echo(
                ctx,
                f"{label}: OK ({binary_report['resolved']})",
            )
            if binary_report["version"]:
                echo(ctx, f"  {binary_report['version']}")
        else:
            echo(
                ctx,
                f"{label}: MISSING ({binary_report['requested']})",
            )
            if binary_report["error"]:
                echo(ctx, f"  {binary_report['error']}")

    capabilities = report.get("capabilities")
    if capabilities:
        missing_encoders = [name for name, available in capabilities["core_encoders"].items() if not available]
        missing_filters = [name for name, available in capabilities["core_filters"].items() if not available]
        echo(
            ctx,
            "Capabilities: "
            f"{capabilities['encoder_count']} encoders, "
            f"{capabilities['decoder_count']} decoders, "
            f"{capabilities['filter_count']} filters, "
            f"{capabilities['muxer_count']} muxers, "
            f"{capabilities['demuxer_count']} demuxers",
        )
        echo(
            ctx,
            f"Protocols: {len(capabilities['input_protocols'])} input, {len(capabilities['output_protocols'])} output",
        )
        subtitle_support = capabilities["subtitle_support"]
        echo(
            ctx,
            "Subtitles: "
            f"encoders={','.join(subtitle_support['text_encoders']) or 'none'}, "
            f"burn-filter={'yes' if subtitle_support['burn_filter'] else 'no'}",
        )
        echo(ctx, f"Hardware acceleration: {', '.join(capabilities['hardware_accelerators']) or 'none reported'}")
        if missing_encoders:
            echo(ctx, f"Optional core encoders missing: {', '.join(missing_encoders)}")
        if missing_filters:
            echo(ctx, f"Optional core filters missing: {', '.join(missing_filters)}")


def handle_doctor(args: argparse.Namespace) -> int:
    """
    Run the diagnostic command.
    """
    ctx = build_context(args)
    report = collect_doctor_report(ctx)
    exit_code = EXIT_OK
    if not report["ffmpeg"]["available"] or not report["ffprobe"]["available"]:
        exit_code = EXIT_ENVIRONMENT_ERROR

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        render_doctor_report(ctx, report)

    return exit_code


def _run_smoke_test(ctx: CLIContext, workspace: Path, retained: bool) -> dict[str, Any]:
    """
    Generate and verify a tiny local workflow without repository fixtures.
    """
    workspace.mkdir(parents=True, exist_ok=True)
    input_path = workspace / "synthetic-input.mp4"
    thumbnail_path = workspace / "synthetic-thumbnail.jpg"
    runner = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path)

    generation = runner.run(
        [
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=660:sample_rate=44100",
            "-t",
            "1",
            "-c:v",
            "mpeg4",
            "-q:v",
            "8",
            "-c:a",
            "aac",
            "-pix_fmt",
            "yuv420p",
            "-shortest",
            "-y",
            str(input_path),
        ]
    )
    raise_for_completed_process_error(generation)

    thumbnail = runner.extract_thumbnail(
        str(input_path),
        str(thumbnail_path),
        timestamp="00:00:00.200",
        width=160,
        quality=3,
    )
    raise_for_completed_process_error(thumbnail)

    probe = FFprobeRunner(ffprobe_path=ctx.ffprobe_path)
    input_metadata = probe.probe(str(input_path))
    thumbnail_metadata = probe.probe(str(thumbnail_path))
    video = input_metadata.get("video", {})
    image = thumbnail_metadata.get("video", {})
    if video.get("width") != 320 or video.get("height") != 180:
        raise CLIError("Synthetic video verification returned an unexpected resolution.")
    if image.get("width") != 160:
        raise CLIError("Synthetic thumbnail verification returned an unexpected width.")

    return {
        "schema_version": "1.0",
        "status": "ok",
        "retained": retained,
        "workspace": str(workspace.resolve()) if retained else None,
        "input": {
            "filename": input_path.name,
            "size_bytes": input_path.stat().st_size,
            "format": input_metadata.get("format_name"),
            "duration_seconds": input_metadata.get("duration"),
            "video": input_metadata.get("video"),
            "audio": input_metadata.get("audio"),
        },
        "output": {
            "filename": thumbnail_path.name,
            "size_bytes": thumbnail_path.stat().st_size,
            "image": thumbnail_metadata.get("video"),
        },
    }


def _render_smoke_report(ctx: CLIContext, report: dict[str, Any]) -> None:
    """
    Render a compact human-readable smoke-test summary.
    """
    video = report["input"]["video"]
    image = report["output"]["image"]
    echo(ctx, "Smoke test: PASS")
    echo(
        ctx,
        f"Synthetic input: {video.get('codec', 'unknown')} "
        f"{video.get('width')}x{video.get('height')} "
        f"({format_bytes(report['input']['size_bytes'])})",
    )
    echo(
        ctx,
        f"Verified thumbnail: {image.get('width')}x{image.get('height')} "
        f"({format_bytes(report['output']['size_bytes'])})",
    )
    if report["retained"]:
        echo(ctx, f"Artifacts: {report['workspace']}")
    else:
        echo(ctx, "Artifacts: cleaned up")


def handle_smoke_test(args: argparse.Namespace) -> int:
    """
    Run a package-installed synthetic end-to-end verification.
    """
    ctx = build_context(args)
    if args.keep_dir is not None:
        workspace = prepare_output_dir(str(args.keep_dir), force=ctx.force, option_name="--keep-dir")
        report = _run_smoke_test(ctx, workspace, retained=True)
    else:
        with tempfile.TemporaryDirectory(prefix="pyffmpegcore-smoke-") as temp_dir:
            report = _run_smoke_test(ctx, Path(temp_dir), retained=False)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _render_smoke_report(ctx, report)
    return EXIT_OK


def render_probe_report(ctx: CLIContext, metadata: dict[str, Any]) -> None:
    """
    Print a human-readable media summary.
    """
    echo(ctx, f"File: {metadata.get('filename', 'unknown')}")
    echo(ctx, f"Format: {metadata.get('format_long_name') or metadata.get('format_name') or 'unknown'}")
    duration = metadata.get("duration")
    if duration is not None:
        echo(ctx, f"Duration: {duration:.2f} seconds")
    if metadata.get("size") is not None:
        echo(ctx, f"Size: {metadata['size']} bytes")
    if metadata.get("bit_rate") is not None:
        echo(ctx, f"Bitrate: {metadata['bit_rate']} bps")

    video = metadata.get("video")
    if video:
        echo(ctx, "Video stream:")
        echo(ctx, f"  Codec: {video.get('codec', 'unknown')}")
        echo(ctx, f"  Resolution: {video.get('width', '?')}x{video.get('height', '?')}")
        if video.get("duration") is not None:
            echo(ctx, f"  Duration: {video['duration']}")

    audio = metadata.get("audio")
    if audio:
        echo(ctx, "Audio stream:")
        echo(ctx, f"  Codec: {audio.get('codec', 'unknown')}")
        if audio.get("sample_rate") is not None:
            echo(ctx, f"  Sample rate: {audio['sample_rate']} Hz")
        if audio.get("channels") is not None:
            echo(ctx, f"  Channels: {audio['channels']}")

    chapters = metadata.get("chapters", [])
    if chapters:
        echo(ctx, f"Chapters: {len(chapters)}")


def handle_probe(args: argparse.Namespace) -> int:
    """
    Run the probe command.
    """
    ctx = build_context(args)
    input_path = require_existing_input(args.input)

    try:
        metadata = FFprobeRunner(ffprobe_path=ctx.ffprobe_path).probe(str(input_path))
    except RuntimeError as exc:
        message = str(exc)
        exit_code = EXIT_ENVIRONMENT_ERROR if "was not found" in message else EXIT_RUNTIME_ERROR
        raise CLIError(message, exit_code=exit_code) from exc

    if args.json:
        print(json.dumps(metadata, indent=2))
    else:
        render_probe_report(ctx, metadata)

    return EXIT_OK


def raise_for_completed_process_error(result: subprocess.CompletedProcess | JobResult) -> None:
    """
    Raise a user-facing CLI error when an FFmpeg command fails.
    """
    if result.returncode == 0:
        return

    raise CLIError(result.stderr or "FFmpeg command failed.", exit_code=EXIT_RUNTIME_ERROR)


def summarize_output_file(ctx: CLIContext, output_path: Path) -> None:
    """
    Print a lightweight summary for a generated media file.
    """
    try:
        metadata = FFprobeRunner(ffprobe_path=ctx.ffprobe_path).probe(str(output_path))
    except RuntimeError:
        echo(ctx, f"Output: {output_path}")
        return

    echo(ctx, f"Output: {output_path}")
    if metadata.get("format_name"):
        echo(ctx, f"Container: {metadata['format_name']}")
    if metadata.get("duration") is not None:
        echo(ctx, f"Duration: {metadata['duration']:.2f} seconds")
    if metadata.get("size") is not None:
        echo(ctx, f"Size: {format_bytes(metadata['size'])}")
    if metadata.get("video"):
        video = metadata["video"]
        echo(ctx, f"Video: {video.get('codec', 'unknown')} {video.get('width', '?')}x{video.get('height', '?')}")
    if metadata.get("audio"):
        audio = metadata["audio"]
        echo(ctx, f"Audio: {audio.get('codec', 'unknown')}")


def build_progress_printer(ctx: CLIContext, input_path: Path) -> CLIProgressPrinter | None:
    """
    Create a progress printer when command output is not quiet.
    """
    if ctx.quiet:
        return None

    try:
        duration = FFprobeRunner(ffprobe_path=ctx.ffprobe_path).get_duration(str(input_path))
    except RuntimeError:
        duration = None

    return CLIProgressPrinter(total_duration=duration or None)


def report_batch_results(ctx: CLIContext, label: str, results: dict[str, int]) -> None:
    """
    Print a concise batch summary.
    """
    echo(
        ctx,
        (f"{label}: {results['successful']} succeeded, {results['failed']} failed, {results['total']} total"),
    )


def _execution_exit_code(bundle: CLIExecutionBundle) -> int:
    """Map stable item outcomes to the documented CLI exit categories."""
    if bundle.failed_count == 0:
        return EXIT_OK
    if bundle.succeeded_count:
        return EXIT_PARTIAL_SUCCESS
    categories = {item.result.exit_category for item in bundle.items}
    if categories == {"environment"}:
        return EXIT_ENVIRONMENT_ERROR
    if categories <= {"validation"}:
        return EXIT_VALIDATION_ERROR
    return EXIT_RUNTIME_ERROR


def _render_execution_failures(bundle: CLIExecutionBundle) -> None:
    """Write actionable item failures to stderr without corrupting JSON stdout."""
    for item in bundle.items:
        if item.result.succeeded:
            continue
        label = item.input or item.output or item.result.workflow
        diagnostic = (item.result.stderr or "FFmpeg command failed.").strip()
        echo_error(f"{label}: {diagnostic}")


def _render_execution_successes(ctx: CLIContext, bundle: CLIExecutionBundle) -> None:
    """Keep the established human summaries on top of typed results."""
    if bundle.prepared.plan.workflow.startswith("images/"):
        labels = {
            "images/convert": "Image conversion",
            "images/optimize": "Image optimization",
            "images/webp": "Image WebP conversion",
        }
        report_batch_results(
            ctx,
            labels[bundle.prepared.plan.workflow],
            {
                "total": len(bundle.items),
                "successful": bundle.succeeded_count,
                "failed": bundle.failed_count,
            },
        )
        return
    for item in bundle.items:
        if item.result.succeeded and item.output is not None:
            summarize_output_file(ctx, Path(item.output))


def handle_planned_execution(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Plan, preflight, execute, and render every media-writing CLI command."""
    prepared = prepare_cli_job(args)
    result_json = bool(getattr(args, "result_json", False))
    progress_printer: CLIProgressPrinter | None = None
    if not ctx.quiet and not result_json and prepared.plan.inputs:
        progress_printer = build_progress_printer(ctx, Path(prepared.plan.inputs[0]))

    def report_progress(event: ProgressEvent) -> None:
        if progress_printer is not None:
            progress_printer(event.to_dict())

    bundle = execute_prepared_cli_job(
        prepared,
        progress_callback=report_progress if progress_printer is not None else None,
    )
    if result_json:
        print(json.dumps(bundle.to_dict(), indent=2))
    else:
        _render_execution_failures(bundle)
        _render_execution_successes(ctx, bundle)
    return _execution_exit_code(bundle)


def handle_planned_command(args: argparse.Namespace) -> int:
    """Argparse target shared by every media-writing command."""
    return handle_planned_execution(args, build_context(args))


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the CLI.
    """
    parser = build_parser()
    argv = list(argv) if argv is not None else sys.argv[1:]

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE_ERROR

    if not argv:
        parser.print_help()
        return EXIT_OK

    handler = getattr(args, "handler", None)
    if handler is None:
        echo_error("A complete command is required. Run `pyffmpegcore --help` for usage.")
        parser.print_usage(file=sys.stderr)
        return EXIT_USAGE_ERROR

    try:
        ctx = build_context(args)
        echo_verbose(ctx, f"command={getattr(args, 'command', None)}")
        echo_verbose(ctx, f"ffmpeg={ctx.ffmpeg_path}")
        echo_verbose(ctx, f"ffprobe={ctx.ffprobe_path}")
        preview = bool(getattr(args, "dry_run", False) or getattr(args, "explain", False))
        if getattr(args, "plan_json", False) and not preview:
            raise CLIError("--plan-json requires --dry-run or --explain.", exit_code=EXIT_USAGE_ERROR)
        if getattr(args, "result_json", False) and preview:
            raise CLIError("--result-json cannot be combined with --dry-run or --explain.", exit_code=EXIT_USAGE_ERROR)
        if getattr(args, "result_json", False) and getattr(args, "command", None) not in WRITING_COMMANDS:
            raise CLIError("--result-json requires a media-writing command.", exit_code=EXIT_USAGE_ERROR)
        if getattr(args, "timeout", None) is not None and getattr(args, "command", None) not in WRITING_COMMANDS:
            raise CLIError("--timeout requires a media-writing command.", exit_code=EXIT_USAGE_ERROR)
        if getattr(args, "temp_files", "clean") != "clean" and getattr(args, "command", None) not in WRITING_COMMANDS:
            raise CLIError("--temp-files requires a media-writing command.", exit_code=EXIT_USAGE_ERROR)
        if preview:
            plan = build_cli_plan(args)
            preflight = PreflightEngine(ffmpeg_path=ctx.ffmpeg_path, ffprobe_path=ctx.ffprobe_path).check(plan)
            if args.plan_json:
                print(render_plan_json(plan, preflight))
            else:
                print(render_plan_text(plan, preflight, explain=bool(args.explain)))
            return EXIT_OK if preflight.ok else EXIT_VALIDATION_ERROR
        return int(handler(args))
    except CLIError as exc:
        echo_error(str(exc))
        return exc.exit_code
    except ValidationError as exc:
        echo_error(str(exc))
        return EXIT_VALIDATION_ERROR
    except RuntimeError as exc:
        cli_error = runtime_error_to_cli_error(exc)
        echo_error(str(cli_error))
        return cli_error.exit_code
    except ValueError as exc:
        echo_error(str(exc))
        return EXIT_VALIDATION_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
