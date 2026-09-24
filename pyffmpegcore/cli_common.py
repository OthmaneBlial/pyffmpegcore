"""Shared CLI context, output helpers, and stable exit codes."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from ._terminal import terminal_safe_text

EXIT_OK = 0
EXIT_ENVIRONMENT_ERROR = 3
EXIT_USAGE_ERROR = 2
EXIT_VALIDATION_ERROR = 4
EXIT_RUNTIME_ERROR = 5
EXIT_PARTIAL_SUCCESS = 6


@dataclass
class CLIContext:
    """Shared execution context derived from parsed CLI arguments."""

    verbose: bool = False
    quiet: bool = False
    force: bool = False
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"


def build_context(args: argparse.Namespace) -> CLIContext:
    """Build a shared CLI context from parsed arguments."""
    return CLIContext(
        verbose=getattr(args, "verbose", False),
        quiet=getattr(args, "quiet", False),
        force=getattr(args, "force", False),
        ffmpeg_path=getattr(args, "ffmpeg_path", "ffmpeg"),
        ffprobe_path=getattr(args, "ffprobe_path", "ffprobe"),
    )


def echo(ctx: CLIContext, message: str) -> None:
    """Print a human-readable message unless quiet mode is enabled."""
    if not ctx.quiet:
        print(terminal_safe_text(message))


def echo_block(ctx: CLIContext, message: str) -> None:
    """Print rendered layout while escaping embedded terminal controls."""
    if not ctx.quiet:
        print(terminal_safe_text(message, preserve_newlines=True))


def echo_verbose(ctx: CLIContext, message: str) -> None:
    """Print diagnostic detail to stderr when verbose mode is enabled."""
    if ctx.verbose:
        print(terminal_safe_text(f"[verbose] {message}"), file=sys.stderr)


def echo_error(message: str) -> None:
    """Print a user-facing error message to stderr."""
    print(terminal_safe_text(message), file=sys.stderr)
