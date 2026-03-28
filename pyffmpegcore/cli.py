"""
Command-line entrypoint for PyFFmpegCore.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Sequence

from . import __version__
from .probe import FFprobeRunner
from .runner import FFmpegRunner, escape_path_for_concat, escape_path_for_filter


EXIT_OK = 0
EXIT_ENVIRONMENT_ERROR = 3
EXIT_USAGE_ERROR = 2
EXIT_RUNTIME_ERROR = 5
EXIT_PARTIAL_SUCCESS = 6

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


class CLIError(RuntimeError):
    """
    User-facing CLI error with a stable exit code.
    """

    def __init__(self, message: str, exit_code: int = EXIT_RUNTIME_ERROR):
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


def add_global_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add global CLI arguments shared by the root parser and future subcommands.
    """
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "--verbose",
        action="store_true",
        help="Show more detailed command output.",
    )
    verbosity.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce command output to essentials.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting existing output files or directories.",
    )
    parser.add_argument(
        "--ffmpeg-path",
        default="ffmpeg",
        help="Path to the ffmpeg executable. Defaults to %(default)s.",
    )
    parser.add_argument(
        "--ffprobe-path",
        default="ffprobe",
        help="Path to the ffprobe executable. Defaults to %(default)s.",
    )


def build_global_parent() -> argparse.ArgumentParser:
    """
    Build the shared parent parser used by the root parser and subcommands.
    """
    parent = argparse.ArgumentParser(add_help=False)
    add_global_arguments(parent)
    return parent


def build_parser() -> argparse.ArgumentParser:
    """
    Build the top-level CLI parser.
    """
    common_parent = build_global_parent()
    parser = argparse.ArgumentParser(
        prog="pyffmpegcore",
        parents=[common_parent],
        description=(
            "PyFFmpegCore CLI. A task-focused terminal interface for the "
            "verified media workflows in this repository."
        ),
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
    convert_parser.set_defaults(handler=handle_convert)

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
    compress_parser.add_argument(
        "--target-size-kb",
        type=int,
        help="Target output size in kilobytes for two-pass compression.",
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
    compress_parser.set_defaults(handler=handle_compress)

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
    extract_audio_parser.set_defaults(handler=handle_extract_audio)

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
    thumbnail_parser.set_defaults(handler=handle_thumbnail)

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
    waveform_parser.set_defaults(handler=handle_waveform)

    speed_parser = subparsers.add_parser(
        "speed",
        parents=[common_parent],
        help="Change playback speed for video or audio media.",
        description="Change playback speed for video or audio media.",
    )
    speed_subparsers = speed_parser.add_subparsers(dest="speed_command", metavar="SPEED_COMMAND")

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
    speed_video_parser.set_defaults(handler=handle_speed_video)

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
    speed_audio_parser.set_defaults(handler=handle_speed_audio)

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
    concat_parser.set_defaults(handler=handle_concat)

    subtitles_parser = subparsers.add_parser(
        "subtitles",
        parents=[common_parent],
        help="Add, extract, or burn subtitle tracks.",
        description="Add, extract, or burn subtitle tracks.",
    )
    subtitles_subparsers = subtitles_parser.add_subparsers(
        dest="subtitles_command",
        metavar="SUBTITLES_COMMAND",
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
    subtitles_add_parser.set_defaults(handler=handle_subtitles_add)

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
    subtitles_extract_parser.set_defaults(handler=handle_subtitles_extract)

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
    subtitles_burn_parser.set_defaults(handler=handle_subtitles_burn)

    mix_audio_parser = subparsers.add_parser(
        "mix-audio",
        parents=[common_parent],
        help="Mix, concatenate, mash up, or layer multiple audio sources.",
        description="Mix, concatenate, mash up, or layer multiple audio sources.",
    )
    mix_audio_subparsers = mix_audio_parser.add_subparsers(
        dest="mix_audio_command",
        metavar="MIX_AUDIO_COMMAND",
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
    mix_audio_mix_parser.set_defaults(handler=handle_mix_audio_mix)

    mix_audio_concat_parser = mix_audio_subparsers.add_parser(
        "concat",
        parents=[common_parent],
        help="Concatenate audio files one after another.",
        description="Concatenate audio files one after another.",
    )
    mix_audio_concat_parser.add_argument("--inputs", nargs="+", required=True, help="Audio input paths.")
    mix_audio_concat_parser.add_argument("--output", required=True, help="Merged audio output path.")
    mix_audio_concat_parser.set_defaults(handler=handle_mix_audio_concat)

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
    mix_audio_mashup_parser.set_defaults(handler=handle_mix_audio_mashup)

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
    mix_audio_background_parser.set_defaults(handler=handle_mix_audio_background)

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
    normalize_audio_parser.set_defaults(handler=handle_normalize_audio)

    images_parser = subparsers.add_parser(
        "images",
        parents=[common_parent],
        help="Batch-convert or optimize image directories.",
        description="Batch-convert or optimize image directories.",
    )
    images_subparsers = images_parser.add_subparsers(dest="images_command", metavar="IMAGES_COMMAND")

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
    images_convert_parser.set_defaults(handler=handle_images_convert)

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
    images_optimize_parser.set_defaults(handler=handle_images_optimize)

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
    images_webp_parser.set_defaults(handler=handle_images_webp)

    return parser


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


def echo_error(message: str) -> None:
    """
    Print a user-facing error message to stderr.
    """
    print(message, file=sys.stderr)


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
    resolved = str(Path(binary_path).resolve()) if is_explicit_path and Path(binary_path).exists() else shutil.which(binary_path)
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
        report["version"] = result.stdout.splitlines()[0] if result.stdout else ""
        return report

    report["error"] = result.stderr.strip() or "Version probe failed"
    return report


def collect_doctor_report(ctx: CLIContext) -> dict[str, Any]:
    """
    Collect environment diagnostics for the CLI.
    """
    ffmpeg = inspect_binary(ctx.ffmpeg_path)
    ffprobe = inspect_binary(ctx.ffprobe_path)
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


def raise_for_completed_process_error(result: subprocess.CompletedProcess) -> None:
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


def handle_convert(args: argparse.Namespace) -> int:
    """
    Run the convert command.
    """
    ctx = build_context(args)
    input_path = require_existing_input(args.input)
    output_path = prepare_output_path(args.output, force=ctx.force)

    kwargs = {
        key: value
        for key, value in {
            "video_codec": args.video_codec,
            "audio_codec": args.audio_codec,
            "video_bitrate": args.video_bitrate,
            "audio_bitrate": args.audio_bitrate,
            "pix_fmt": args.pix_fmt,
            "threads": args.threads,
        }.items()
        if value is not None
    }

    try:
        result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).convert(
            str(input_path),
            str(output_path),
            audio_only=args.audio_only,
            **kwargs,
        )
    except RuntimeError as exc:
        message = str(exc)
        exit_code = EXIT_ENVIRONMENT_ERROR if "was not found" in message else EXIT_RUNTIME_ERROR
        raise CLIError(message, exit_code=exit_code) from exc

    raise_for_completed_process_error(result)
    summarize_output_file(ctx, output_path)
    return EXIT_OK


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


def handle_compress(args: argparse.Namespace) -> int:
    """
    Run the compress command.
    """
    ctx = build_context(args)
    input_path = require_existing_input(args.input)
    output_path = prepare_output_path(args.output, force=ctx.force)

    kwargs = {
        key: value
        for key, value in {
            "video_codec": args.video_codec,
            "audio_codec": args.audio_codec,
            "video_bitrate": args.video_bitrate,
            "audio_bitrate": args.audio_bitrate,
            "preset": args.preset,
            "threads": args.threads,
        }.items()
        if value is not None
    }

    progress_callback = build_progress_printer(ctx, input_path)

    try:
        result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).compress(
            str(input_path),
            str(output_path),
            target_size_kb=args.target_size_kb,
            crf=args.crf,
            two_pass=args.two_pass,
            progress_callback=progress_callback,
            **kwargs,
        )
    except (RuntimeError, ValueError) as exc:
        message = str(exc)
        exit_code = EXIT_ENVIRONMENT_ERROR if "was not found" in message else EXIT_RUNTIME_ERROR
        raise CLIError(message, exit_code=exit_code) from exc

    raise_for_completed_process_error(result)
    summarize_output_file(ctx, output_path)
    return EXIT_OK


def handle_extract_audio(args: argparse.Namespace) -> int:
    """
    Run the extract-audio command.
    """
    ctx = build_context(args)
    input_path = require_existing_input(args.input)
    output_path = prepare_output_path(args.output, force=ctx.force)

    kwargs = {
        key: value
        for key, value in {
            "audio_codec": args.audio_codec,
            "audio_bitrate": args.audio_bitrate,
            "sample_rate": args.sample_rate,
            "channels": args.channels,
            "threads": args.threads,
        }.items()
        if value is not None
    }

    progress_callback = build_progress_printer(ctx, input_path)

    try:
        result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).extract_audio(
            str(input_path),
            str(output_path),
            progress_callback=progress_callback,
            **kwargs,
        )
    except RuntimeError as exc:
        message = str(exc)
        exit_code = EXIT_ENVIRONMENT_ERROR if "was not found" in message else EXIT_RUNTIME_ERROR
        raise CLIError(message, exit_code=exit_code) from exc

    raise_for_completed_process_error(result)
    summarize_output_file(ctx, output_path)
    return EXIT_OK


def handle_thumbnail(args: argparse.Namespace) -> int:
    """
    Run the thumbnail command.
    """
    ctx = build_context(args)
    input_path = require_existing_input(args.input)
    output_path = prepare_output_path(args.output, force=ctx.force)

    try:
        result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).extract_thumbnail(
            str(input_path),
            str(output_path),
            timestamp=args.timestamp,
            width=args.width,
            height=args.height,
            quality=args.quality,
        )
    except (RuntimeError, ValueError) as exc:
        message = str(exc)
        exit_code = EXIT_ENVIRONMENT_ERROR if "was not found" in message else EXIT_RUNTIME_ERROR
        raise CLIError(message, exit_code=exit_code) from exc

    raise_for_completed_process_error(result)
    summarize_output_file(ctx, output_path)
    return EXIT_OK


def handle_waveform(args: argparse.Namespace) -> int:
    """
    Run the waveform command.
    """
    ctx = build_context(args)
    input_path = require_existing_input(args.input)
    output_path = prepare_output_path(args.output, force=ctx.force)

    try:
        result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).generate_waveform(
            str(input_path),
            str(output_path),
            width=args.width,
            height=args.height,
            colors=args.colors,
        )
    except (RuntimeError, ValueError) as exc:
        message = str(exc)
        exit_code = EXIT_ENVIRONMENT_ERROR if "was not found" in message else EXIT_RUNTIME_ERROR
        raise CLIError(message, exit_code=exit_code) from exc

    raise_for_completed_process_error(result)
    summarize_output_file(ctx, output_path)
    return EXIT_OK


def build_atempo_chain(speed_factor: float) -> str:
    """
    Build an atempo filter chain for arbitrary positive speed values.
    """
    if speed_factor <= 0:
        raise CLIError("Speed factor must be positive.")

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
    return ",".join(f"atempo={factor}" for factor in factors)


def run_video_speed(
    ctx: CLIContext,
    input_path: Path,
    output_path: Path,
    factor: float,
    preserve_pitch: bool,
) -> None:
    """
    Change playback speed for a video file, preserving audio when present.
    """
    if factor <= 0:
        raise CLIError("Speed factor must be positive.")

    try:
        metadata = FFprobeRunner(ffprobe_path=ctx.ffprobe_path).probe(str(input_path))
    except RuntimeError as exc:
        message = str(exc)
        exit_code = EXIT_ENVIRONMENT_ERROR if "was not found" in message else EXIT_RUNTIME_ERROR
        raise CLIError(message, exit_code=exit_code) from exc

    has_audio = bool(metadata.get("audio"))
    args = ["-i", str(input_path)]

    if has_audio:
        if preserve_pitch:
            audio_filter = build_atempo_chain(factor)
        else:
            sample_rate = metadata.get("audio", {}).get("sample_rate", 44100)
            audio_filter = f"asetrate={sample_rate}*{factor},aresample={sample_rate}"

        filter_complex = (
            f"[0:v]setpts=(PTS-STARTPTS)/{factor}[v];"
            f"[0:a]{audio_filter}[a]"
        )
        args.extend(["-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]"])
    else:
        args.extend(["-vf", f"setpts=(PTS-STARTPTS)/{factor}"])

    args.extend(["-c:v", "libx264"])
    if has_audio:
        args.extend(["-c:a", "aac"])
    args.extend(["-y", str(output_path)])

    result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).run(args)
    raise_for_completed_process_error(result)


def run_audio_speed(
    ctx: CLIContext,
    input_path: Path,
    output_path: Path,
    factor: float,
    preserve_pitch: bool,
) -> None:
    """
    Change playback speed for an audio file.
    """
    if factor <= 0:
        raise CLIError("Speed factor must be positive.")

    try:
        metadata = FFprobeRunner(ffprobe_path=ctx.ffprobe_path).probe(str(input_path))
    except RuntimeError as exc:
        message = str(exc)
        exit_code = EXIT_ENVIRONMENT_ERROR if "was not found" in message else EXIT_RUNTIME_ERROR
        raise CLIError(message, exit_code=exit_code) from exc

    sample_rate = metadata.get("audio", {}).get("sample_rate", 44100)
    if preserve_pitch:
        audio_filter = build_atempo_chain(factor)
    else:
        audio_filter = f"asetrate={sample_rate}*{factor},aresample={sample_rate}"

    args = [
        "-i",
        str(input_path),
        "-filter:a",
        audio_filter,
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-y",
        str(output_path),
    ]
    result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).run(args)
    raise_for_completed_process_error(result)


def handle_speed_video(args: argparse.Namespace) -> int:
    """
    Run the speed video subcommand.
    """
    ctx = build_context(args)
    input_path = require_existing_input(args.input)
    output_path = prepare_output_path(args.output, force=ctx.force)

    run_video_speed(
        ctx,
        input_path,
        output_path,
        args.factor,
        preserve_pitch=not args.no_pitch_preserve,
    )
    summarize_output_file(ctx, output_path)
    return EXIT_OK


def handle_speed_audio(args: argparse.Namespace) -> int:
    """
    Run the speed audio subcommand.
    """
    ctx = build_context(args)
    input_path = require_existing_input(args.input)
    output_path = prepare_output_path(args.output, force=ctx.force)

    run_audio_speed(
        ctx,
        input_path,
        output_path,
        args.factor,
        preserve_pitch=not args.no_pitch_preserve,
    )
    summarize_output_file(ctx, output_path)
    return EXIT_OK


def run_concat_copy(ctx: CLIContext, input_paths: list[Path], output_path: Path) -> None:
    """
    Concatenate matching clips using FFmpeg's concat demuxer.
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
    ) as handle:
        concat_file = Path(handle.name)
        for input_path in input_paths:
            handle.write(f"file {escape_path_for_concat(str(input_path))}\n")

    try:
        result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).run(
            [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c",
                "copy",
                "-y",
                str(output_path),
            ]
        )
    finally:
        if concat_file.exists():
            concat_file.unlink()

    raise_for_completed_process_error(result)


def run_concat_reencode(
    ctx: CLIContext,
    input_paths: list[Path],
    output_path: Path,
    video_codec: str,
    audio_codec: str,
) -> None:
    """
    Concatenate clips by re-encoding them into a shared output format.
    """
    args: list[str] = []
    for input_path in input_paths:
        args.extend(["-i", str(input_path)])

    video_inputs = "".join(f"[{index}:v]" for index in range(len(input_paths)))
    audio_inputs = "".join(f"[{index}:a]" for index in range(len(input_paths)))
    filter_complex = (
        f"{video_inputs}concat=n={len(input_paths)}:v=1:a=0[vout];"
        f"{audio_inputs}concat=n={len(input_paths)}:v=0:a=1[aout]"
    )

    args.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            video_codec,
            "-c:a",
            audio_codec,
            "-y",
            str(output_path),
        ]
    )
    result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).run(args)
    raise_for_completed_process_error(result)


def handle_concat(args: argparse.Namespace) -> int:
    """
    Run the concat command.
    """
    ctx = build_context(args)
    if len(args.inputs) < 2:
        raise CLIError("--inputs requires at least two clips.")

    input_paths = [require_existing_input(path, option_name="--inputs") for path in args.inputs]
    output_path = prepare_output_path(args.output, force=ctx.force)

    try:
        if args.mode == "copy":
            run_concat_copy(ctx, input_paths, output_path)
        else:
            run_concat_reencode(
                ctx,
                input_paths,
                output_path,
                video_codec=args.video_codec,
                audio_codec=args.audio_codec,
            )
    except RuntimeError as exc:
        message = str(exc)
        exit_code = EXIT_ENVIRONMENT_ERROR if "was not found" in message else EXIT_RUNTIME_ERROR
        raise CLIError(message, exit_code=exit_code) from exc

    summarize_output_file(ctx, output_path)
    return EXIT_OK


def handle_subtitles_add(args: argparse.Namespace) -> int:
    """
    Add an external subtitle track to a video file.
    """
    ctx = build_context(args)
    video_path = require_existing_input(args.video, option_name="--video")
    subtitle_path = require_existing_input(args.subtitle, option_name="--subtitle")
    output_path = prepare_output_path(args.output, force=ctx.force)

    result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).run(
        [
            "-i",
            str(video_path),
            "-i",
            str(subtitle_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-map",
            "1:0",
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-c:s",
            "mov_text",
            "-metadata:s:s:0",
            f"language={args.language}",
            "-y",
            str(output_path),
        ]
    )
    raise_for_completed_process_error(result)
    summarize_output_file(ctx, output_path)
    return EXIT_OK


def handle_subtitles_extract(args: argparse.Namespace) -> int:
    """
    Extract subtitles from a video file.
    """
    ctx = build_context(args)
    video_path = require_existing_input(args.video, option_name="--video")
    output_path = prepare_output_path(args.output, force=ctx.force)

    result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).run(
        [
            "-i",
            str(video_path),
            "-map",
            f"0:s:{args.stream_index}",
            "-c:s",
            "srt",
            "-y",
            str(output_path),
        ]
    )
    raise_for_completed_process_error(result)
    echo(ctx, f"Created: {output_path}")
    return EXIT_OK


def handle_subtitles_burn(args: argparse.Namespace) -> int:
    """
    Burn subtitles into the video image.
    """
    ctx = build_context(args)
    video_path = require_existing_input(args.video, option_name="--video")
    subtitle_path = require_existing_input(args.subtitle, option_name="--subtitle")
    output_path = prepare_output_path(args.output, force=ctx.force)

    temporary_subtitle_file: Path | None = None
    subtitle_source = subtitle_path

    if "'" in str(subtitle_path):
        with tempfile.NamedTemporaryFile(
            suffix=subtitle_path.suffix,
            delete=False,
        ) as temp_file:
            temporary_subtitle_file = Path(temp_file.name)
        shutil.copyfile(subtitle_path, temporary_subtitle_file)
        subtitle_source = temporary_subtitle_file

    subtitle_filter = (
        f"subtitles='{escape_path_for_filter(str(subtitle_source))}':"
        f"force_style='FontSize={args.font_size},PrimaryColour={args.font_color}'"
    )

    try:
        result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).run(
            [
                "-i",
                str(video_path),
                "-vf",
                subtitle_filter,
                "-c:a",
                "copy",
                "-y",
                str(output_path),
            ]
        )
    finally:
        if temporary_subtitle_file and temporary_subtitle_file.exists():
            temporary_subtitle_file.unlink()

    raise_for_completed_process_error(result)
    summarize_output_file(ctx, output_path)
    return EXIT_OK


def select_audio_codec(output_path: Path) -> str:
    """
    Pick a sensible audio codec based on the output extension.
    """
    return _AUDIO_CODEC_BY_EXTENSION.get(output_path.suffix.lower(), "aac")


def append_audio_output_options(args: list[str], output_path: Path, bitrate: str) -> None:
    """
    Add audio codec and bitrate options based on the chosen output extension.
    """
    codec = select_audio_codec(output_path)
    args.extend(["-c:a", codec])
    if bitrate and codec not in _BITRATELESS_AUDIO_CODECS:
        args.extend(["-b:a", bitrate])


def collect_audio_inputs(ctx: CLIContext, input_values: list[str]) -> list[Path]:
    """
    Validate that the provided input files exist and contain audio.
    """
    if len(input_values) < 2:
        raise CLIError("At least two audio inputs are required.")

    valid_inputs: list[Path] = []
    for value in input_values:
        path = require_existing_input(value, option_name="--inputs")
        metadata = FFprobeRunner(ffprobe_path=ctx.ffprobe_path).probe(str(path))
        if not metadata.get("audio"):
            raise CLIError(f"Input does not contain audio: {path}")
        valid_inputs.append(path)

    return valid_inputs


def handle_mix_audio_mix(args: argparse.Namespace) -> int:
    """
    Mix multiple audio sources together.
    """
    ctx = build_context(args)
    input_paths = collect_audio_inputs(ctx, args.inputs)
    output_path = prepare_output_path(args.output, force=ctx.force)

    if args.volumes is not None and len(args.volumes) not in (0, len(input_paths)):
        raise CLIError("--volumes must match the number of --inputs.")

    volumes = args.volumes or [1.0] * len(input_paths)
    filter_parts = []
    ffmpeg_args: list[str] = []
    for input_path in input_paths:
        ffmpeg_args.extend(["-i", str(input_path)])

    for index, volume in enumerate(volumes):
        if volume <= 0:
            raise CLIError("Volume values must be positive.")
        if volume != 1.0:
            filter_parts.append(f"[{index}:a]volume={volume}[a{index}]")
        else:
            filter_parts.append(f"[{index}:a]anull[a{index}]")

    mix_inputs = "".join(f"[a{index}]" for index in range(len(input_paths)))
    filter_parts.append(
        f"{mix_inputs}amix=inputs={len(input_paths)}:duration=longest:normalize=0[aout]"
    )
    ffmpeg_args.extend(["-filter_complex", ";".join(filter_parts), "-map", "[aout]"])
    append_audio_output_options(ffmpeg_args, output_path, bitrate="192k")
    ffmpeg_args.extend(["-y", str(output_path)])

    result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).run(ffmpeg_args)
    raise_for_completed_process_error(result)
    summarize_output_file(ctx, output_path)
    return EXIT_OK


def handle_mix_audio_concat(args: argparse.Namespace) -> int:
    """
    Concatenate audio sources sequentially.
    """
    ctx = build_context(args)
    input_paths = collect_audio_inputs(ctx, args.inputs)
    output_path = prepare_output_path(args.output, force=ctx.force)

    ffmpeg_args: list[str] = []
    for input_path in input_paths:
        ffmpeg_args.extend(["-i", str(input_path)])
    concat_inputs = "".join(f"[{index}:a]" for index in range(len(input_paths)))
    ffmpeg_args.extend(
        [
            "-filter_complex",
            f"{concat_inputs}concat=n={len(input_paths)}:v=0:a=1[aout]",
            "-map",
            "[aout]",
        ]
    )
    append_audio_output_options(ffmpeg_args, output_path, bitrate="192k")
    ffmpeg_args.extend(["-y", str(output_path)])

    result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).run(ffmpeg_args)
    raise_for_completed_process_error(result)
    summarize_output_file(ctx, output_path)
    return EXIT_OK


def handle_mix_audio_mashup(args: argparse.Namespace) -> int:
    """
    Create a crossfaded mashup from multiple audio sources.
    """
    ctx = build_context(args)
    input_paths = collect_audio_inputs(ctx, args.inputs)
    output_path = prepare_output_path(args.output, force=ctx.force)

    if args.crossfade_duration <= 0:
        raise CLIError("--crossfade-duration must be positive.")

    ffmpeg_args: list[str] = []
    for input_path in input_paths:
        ffmpeg_args.extend(["-i", str(input_path)])

    filter_parts = []
    current_label = "[0:a]"
    for index in range(1, len(input_paths)):
        next_label = f"[a{index}]"
        filter_parts.append(
            f"{current_label}[{index}:a]acrossfade="
            f"d={args.crossfade_duration}:c1=tri:c2=tri{next_label}"
        )
        current_label = next_label
    ffmpeg_args.extend(["-filter_complex", ";".join(filter_parts), "-map", current_label])
    append_audio_output_options(ffmpeg_args, output_path, bitrate="256k")
    ffmpeg_args.extend(["-y", str(output_path)])

    result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).run(ffmpeg_args)
    raise_for_completed_process_error(result)
    summarize_output_file(ctx, output_path)
    return EXIT_OK


def handle_mix_audio_background(args: argparse.Namespace) -> int:
    """
    Layer background audio under a main audio source.
    """
    ctx = build_context(args)
    main_input = require_existing_input(args.main_input, option_name="--main-input")
    background_input = require_existing_input(args.background_input, option_name="--background-input")
    output_path = prepare_output_path(args.output, force=ctx.force)

    for label, path in (("main", main_input), ("background", background_input)):
        metadata = FFprobeRunner(ffprobe_path=ctx.ffprobe_path).probe(str(path))
        if not metadata.get("audio"):
            raise CLIError(f"{label.capitalize()} input does not contain audio: {path}")

    if args.bg_volume <= 0:
        raise CLIError("--bg-volume must be positive.")

    ffmpeg_args = [
        "-i",
        str(main_input),
        "-i",
        str(background_input),
        "-filter_complex",
        f"[1:a]volume={args.bg_volume}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0[aout]",
        "-map",
        "[aout]",
    ]
    append_audio_output_options(ffmpeg_args, output_path, bitrate="192k")
    ffmpeg_args.extend(["-y", str(output_path)])

    result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).run(ffmpeg_args)
    raise_for_completed_process_error(result)
    summarize_output_file(ctx, output_path)
    return EXIT_OK


def handle_normalize_audio(args: argparse.Namespace) -> int:
    """
    Normalize or master an audio track.
    """
    ctx = build_context(args)
    input_path = require_existing_input(args.input)
    output_path = prepare_output_path(args.output, force=ctx.force)

    if args.method == "loudnorm":
        filter_chain = f"loudnorm=I={args.target_i}:TP={args.target_tp}:LRA={args.target_lra}"
        bitrate = "192k"
    else:
        filter_chain = (
            "loudnorm=I=-16:TP=-1.5:LRA=11,"
            "compand=attacks=0.0001:decays=0.2:points=-70/-70|-60/-20|-20/-20|20/20,"
            "alimiter=limit=-1dB:level=disabled"
        )
        bitrate = "256k"

    ffmpeg_args = ["-i", str(input_path), "-af", filter_chain]
    append_audio_output_options(ffmpeg_args, output_path, bitrate=bitrate)
    ffmpeg_args.extend(["-y", str(output_path)])

    result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).run(ffmpeg_args)
    raise_for_completed_process_error(result)
    summarize_output_file(ctx, output_path)
    return EXIT_OK


def collect_image_files(input_dir: Path) -> list[Path]:
    """
    Collect supported image files from a directory.
    """
    patterns = ["*.png", "*.jpg", "*.jpeg", "*.tiff", "*.bmp", "*.gif"]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(sorted(input_dir.glob(pattern)))
    return files


def convert_single_image(
    ctx: CLIContext,
    input_path: Path,
    output_path: Path,
    quality: int,
    resize: tuple[int, int] | None = None,
) -> bool:
    """
    Convert a single image using FFmpeg.
    """
    ffmpeg_args = ["-i", str(input_path)]

    if resize is not None:
        ffmpeg_args.extend(["-vf", f"scale={resize[0]}:{resize[1]}"])

    output_ext = output_path.suffix.lower()
    if output_ext in {".jpg", ".jpeg"}:
        ffmpeg_args.extend(["-q:v", str(min(31, max(1, 31 - int(quality * 31 / 100))))])
    elif output_ext == ".webp":
        ffmpeg_args.extend(["-quality", str(quality)])
    elif output_ext == ".png":
        ffmpeg_args.extend(["-compression_level", str(min(9, max(0, 9 - int(quality * 9 / 100))))])

    ffmpeg_args.extend(["-frames:v", "1"])
    if output_ext in {".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
        ffmpeg_args.extend(["-update", "1"])
    ffmpeg_args.extend(["-y", str(output_path)])

    result = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path).run(ffmpeg_args)
    return result.returncode == 0


def report_batch_results(ctx: CLIContext, label: str, results: dict[str, int]) -> None:
    """
    Print a concise batch summary.
    """
    echo(
        ctx,
        (
            f"{label}: {results['successful']} succeeded, "
            f"{results['failed']} failed, {results['total']} total"
        ),
    )


def finalize_batch_results(results: dict[str, int]) -> int:
    """
    Translate batch results into a stable CLI exit code.
    """
    return EXIT_PARTIAL_SUCCESS if results["failed"] else EXIT_OK


def handle_images_convert(args: argparse.Namespace) -> int:
    """
    Convert a directory of images into another format.
    """
    ctx = build_context(args)
    input_dir = require_existing_input(args.input_dir, option_name="--input-dir")
    output_dir = prepare_output_dir(args.output_dir, force=ctx.force)
    resize = tuple(args.resize) if args.resize is not None else None

    image_files = collect_image_files(input_dir)
    results = {"total": len(image_files), "successful": 0, "failed": 0}
    for image_file in image_files:
        output_path = output_dir / f"{image_file.stem}.{args.format.lstrip('.')}"
        if convert_single_image(ctx, image_file, output_path, quality=args.quality, resize=resize):
            results["successful"] += 1
        else:
            results["failed"] += 1

    report_batch_results(ctx, "Image conversion", results)
    return finalize_batch_results(results)


def handle_images_optimize(args: argparse.Namespace) -> int:
    """
    Optimize a directory of images for web-friendly output.
    """
    ctx = build_context(args)
    input_dir = require_existing_input(args.input_dir, option_name="--input-dir")
    output_dir = prepare_output_dir(args.output_dir, force=ctx.force)
    image_files = collect_image_files(input_dir)
    results = {"total": len(image_files), "successful": 0, "failed": 0}
    prober = FFprobeRunner(ffprobe_path=ctx.ffprobe_path)

    for image_file in image_files:
        resize = None
        try:
            metadata = prober.probe(str(image_file))
            if metadata.get("video"):
                width = metadata["video"].get("width", 0)
                height = metadata["video"].get("height", 0)
                if width > args.max_width or height > args.max_height:
                    ratio = min(args.max_width / width, args.max_height / height)
                    resize = (int(width * ratio), int(height * ratio))
        except RuntimeError:
            results["failed"] += 1
            continue

        output_path = output_dir / f"{image_file.stem}.jpg"
        if convert_single_image(ctx, image_file, output_path, quality=args.quality, resize=resize):
            results["successful"] += 1
        else:
            results["failed"] += 1

    report_batch_results(ctx, "Image optimization", results)
    return finalize_batch_results(results)


def handle_images_webp(args: argparse.Namespace) -> int:
    """
    Convert a directory of images into WebP outputs.
    """
    ctx = build_context(args)
    input_dir = require_existing_input(args.input_dir, option_name="--input-dir")
    output_dir = prepare_output_dir(args.output_dir, force=ctx.force)
    image_files = collect_image_files(input_dir)
    results = {"total": len(image_files), "successful": 0, "failed": 0}

    for image_file in image_files:
        output_path = output_dir / f"{image_file.stem}.webp"
        if convert_single_image(ctx, image_file, output_path, quality=args.quality):
            results["successful"] += 1
        else:
            results["failed"] += 1

    report_batch_results(ctx, "Image WebP conversion", results)
    return finalize_batch_results(results)


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the CLI.
    """
    parser = build_parser()
    argv = list(argv) if argv is not None else sys.argv[1:]

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    if not argv:
        parser.print_help()
        return EXIT_OK

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return EXIT_OK

    try:
        return int(handler(args))
    except CLIError as exc:
        echo_error(str(exc))
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
