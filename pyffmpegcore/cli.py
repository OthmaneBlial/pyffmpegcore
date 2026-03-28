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
