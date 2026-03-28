"""
Command-line entrypoint for PyFFmpegCore.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Sequence

from . import __version__


EXIT_OK = 0
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


def build_parser() -> argparse.ArgumentParser:
    """
    Build the top-level CLI parser.
    """
    parser = argparse.ArgumentParser(
        prog="pyffmpegcore",
        description=(
            "PyFFmpegCore CLI. A task-focused terminal interface for the "
            "verified media workflows in this repository."
        ),
    )
    add_global_arguments(parser)
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
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

    build_context(args)
    parser.print_help()
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
