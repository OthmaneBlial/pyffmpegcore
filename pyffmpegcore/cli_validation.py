"""CLI-specific validation and stable user-facing error mapping."""

from __future__ import annotations

import argparse
from collections.abc import Collection
from pathlib import Path


class CLIError(RuntimeError):
    """User-facing CLI error with a stable exit code."""

    def __init__(self, message: str, exit_code: int = 4):
        super().__init__(message)
        self.exit_code = exit_code


def validate_global_contract(args: argparse.Namespace, writing_commands: Collection[str]) -> bool:
    """Validate cross-command option combinations and return preview mode."""
    preview = bool(getattr(args, "dry_run", False) or getattr(args, "explain", False))
    command = getattr(args, "command", None)
    is_writing = (
        command in writing_commands
        or (command == "profile" and getattr(args, "profile_command", None) == "run")
        or (command == "batch" and getattr(args, "batch_command", None) == "run")
        or (command == "pipeline" and getattr(args, "pipeline_command", None) == "run")
    )
    if getattr(args, "plan_json", False) and not preview:
        raise CLIError("--plan-json requires --dry-run or --explain.", exit_code=2)
    if getattr(args, "result_json", False) and preview:
        raise CLIError("--result-json cannot be combined with --dry-run or --explain.", exit_code=2)
    if getattr(args, "result_json", False) and not is_writing:
        raise CLIError("--result-json requires a media-writing command.", exit_code=2)
    if getattr(args, "timeout", None) is not None and not is_writing:
        raise CLIError("--timeout requires a media-writing command.", exit_code=2)
    if getattr(args, "temp_files", "clean") != "clean" and not is_writing:
        raise CLIError("--temp-files requires a media-writing command.", exit_code=2)
    receipt = getattr(args, "receipt", None)
    if receipt is not None and not is_writing:
        raise CLIError("--receipt requires a media-writing command.", exit_code=2)
    if receipt is not None and preview:
        raise CLIError("--receipt requires execution and cannot be combined with --dry-run or --explain.", exit_code=2)
    if getattr(args, "hash_content", False) and receipt is None and getattr(args, "receipt_dir", None) is None:
        raise CLIError("--hash-content requires --receipt FILE or --receipt-dir DIR.", exit_code=2)
    return preview


def require_existing_input(path_str: str, option_name: str = "--input") -> Path:
    """Validate that a required input path exists."""
    if not path_str:
        raise CLIError(f"{option_name} is required.")

    path = Path(path_str)
    if not path.exists():
        raise CLIError(f"Input path does not exist: {path}")
    return path


def require_output_path(path_str: str, option_name: str = "--output") -> Path:
    """Validate that a required output path was provided."""
    if not path_str:
        raise CLIError(f"{option_name} is required.")
    return Path(path_str)


def prepare_output_path(path_str: str, force: bool, option_name: str = "--output") -> Path:
    """Validate and prepare a file output path."""
    path = require_output_path(path_str, option_name=option_name)
    if path.exists() and not force:
        raise CLIError(f"Output already exists: {path}. Re-run with --force to overwrite.")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def prepare_output_dir(path_str: str, force: bool, option_name: str = "--output-dir") -> Path:
    """Validate and prepare a directory output path."""
    if not path_str:
        raise CLIError(f"{option_name} is required.")

    path = Path(path_str)
    if path.exists() and any(path.iterdir()) and not force:
        raise CLIError(f"Output directory is not empty: {path}. Re-run with --force to reuse it.")
    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_error_to_cli_error(exc: RuntimeError) -> CLIError:
    """Map helper runtime failures into stable environment or processing categories."""
    message = str(exc)
    return CLIError(message, exit_code=3 if "was not found" in message else 5)
