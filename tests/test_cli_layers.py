"""Architecture contracts for the separated CLI layers."""

from __future__ import annotations

from pyffmpegcore.cli_parser import build_parser
from pyffmpegcore.cli_validation import validate_global_contract


def test_parser_registers_handler_names_without_importing_handlers():
    args = build_parser().parse_args(["doctor"])

    assert args.handler_name == "handle_doctor"
    assert not hasattr(args, "handler")


def test_global_validation_reports_preview_mode():
    args = build_parser().parse_args(["convert", "--input", "in.mp4", "--output", "out.mp4", "--dry-run"])

    assert validate_global_contract(args, {"convert"}) is True
