"""
Command-line entrypoint for PyFFmpegCore.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import __version__


EXIT_OK = 0
EXIT_USAGE_ERROR = 2


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


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the CLI.
    """
    parser = build_parser()
    argv = list(argv) if argv is not None else sys.argv[1:]

    try:
        parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    if not argv:
        parser.print_help()
        return EXIT_OK

    parser.print_help()
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
