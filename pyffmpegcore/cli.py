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
from typing import Any, Sequence

from . import __version__
from .probe import FFprobeRunner
from .runner import FFmpegRunner


EXIT_OK = 0
EXIT_ENVIRONMENT_ERROR = 3
EXIT_USAGE_ERROR = 2
EXIT_RUNTIME_ERROR = 5


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

    def __call__(self, progress: dict[str, Any]) -> None:
        if progress.get("status") == "end":
            print("\rProgress: 100% complete", file=sys.stderr)
            return

        time_seconds = progress.get("time_seconds")
        if time_seconds is not None and self.total_duration:
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
        echo(ctx, f"Created: {output_path}")
        return

    echo(ctx, f"Created: {output_path}")
    if metadata.get("format_name"):
        echo(ctx, f"Format: {metadata['format_name']}")
    if metadata.get("duration") is not None:
        echo(ctx, f"Duration: {metadata['duration']:.2f} seconds")
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
