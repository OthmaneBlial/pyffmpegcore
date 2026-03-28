"""
Tests for CLI help text and completion output.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_root_help_includes_examples_and_completion():
    """
    Root help should surface copyable examples and completion guidance.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Examples:" in result.stdout
    assert "pyffmpegcore completion bash" in result.stdout
    assert "See CLI_HELP.md for task-based copy-paste examples." in result.stdout


def test_cli_help_markdown_mentions_completion_install():
    """
    The standalone CLI help doc should explain completion generation and install paths.
    """
    help_doc = (REPO_ROOT / "CLI_HELP.md").read_text(encoding="utf-8")
    assert "pyffmpegcore completion bash" in help_doc
    assert "~/.local/share/bash-completion/completions/pyffmpegcore" in help_doc
    assert "pyffmpegcore completion powershell" in help_doc


def test_completion_bash_output_mentions_core_commands():
    """
    Bash completion output should register the CLI and expose the command tree.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore", "completion", "bash"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "_pyffmpegcore_completion" in result.stdout
    assert "complete -F _pyffmpegcore_completion pyffmpegcore" in result.stdout
    assert "subtitles" in result.stdout
    assert "mix-audio" in result.stdout


def test_completion_zsh_output_mentions_compdef():
    """
    Zsh completion output should register a compdef function.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore", "completion", "zsh"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "#compdef pyffmpegcore" in result.stdout
    assert "compdef _pyffmpegcore pyffmpegcore" in result.stdout


def test_completion_powershell_output_mentions_argument_completer():
    """
    PowerShell completion output should register a native argument completer.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore", "completion", "powershell"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Register-ArgumentCompleter" in result.stdout
    assert "-CommandName pyffmpegcore" in result.stdout
