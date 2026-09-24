"""
Tests for CLI help text and completion output.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

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
    assert "smoke-test" in result.stdout
    assert "See CLI_HELP.md for task-based copy-paste examples." in result.stdout


def test_cli_help_markdown_mentions_completion_install():
    """
    The standalone CLI help doc should explain completion generation and install paths.
    """
    help_doc = (REPO_ROOT / "CLI_HELP.md").read_text(encoding="utf-8")
    assert "pyffmpegcore completion bash" in help_doc
    assert "~/.local/share/bash-completion/completions/pyffmpegcore" in help_doc
    assert "pyffmpegcore completion powershell" in help_doc
    assert "pyffmpegcore completion fish" in help_doc
    assert "~/.config/fish/completions/pyffmpegcore.fish" in help_doc


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


def test_completion_fish_output_uses_nested_parser_metadata():
    """Fish completion must expose nested commands and their own options."""
    result = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore", "completion", "fish"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "function __pyffmpegcore_completion_path" in result.stdout
    assert "complete -c pyffmpegcore -f" in result.stdout
    assert "case 'root:subtitles'" in result.stdout
    assert "case 'subtitles:burn'" in result.stdout
    assert "-n 'test (__pyffmpegcore_completion_path) = subtitles' -a 'burn'" in result.stdout
    assert "-n 'test (__pyffmpegcore_completion_path) = subtitles__burn' -l subtitle" in result.stdout


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


@pytest.mark.parametrize(
    ("shell", "executable", "suffix"),
    [
        ("bash", "bash", ".bash"),
        ("zsh", "zsh", ".zsh"),
        ("fish", "fish", ".fish"),
        ("powershell", "pwsh", ".ps1"),
    ],
)
def test_completion_scripts_parse_in_available_shells(shell, executable, suffix, tmp_path):
    shell_path = shutil.which(executable)
    if shell_path is None:
        pytest.skip(f"{executable} is not installed")

    generated = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore", "completion", shell],
        capture_output=True,
        text=True,
        check=False,
    )
    assert generated.returncode == 0, generated.stderr

    script_path = tmp_path / f"pyffmpegcore-completion{suffix}"
    script_path.write_text(generated.stdout, encoding="utf-8")
    if shell == "powershell":
        parse_command = (
            "$tokens=$null; $errors=$null; "
            "[System.Management.Automation.Language.Parser]::ParseFile("
            "$env:COMPLETION_FILE, [ref]$tokens, [ref]$errors) | Out-Null; "
            "if ($errors.Count) { $errors | ForEach-Object { [Console]::Error.WriteLine($_) }; exit 1 }"
        )
        environment = os.environ | {"COMPLETION_FILE": str(script_path)}
        parse_command_line = [
            shell_path,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            parse_command,
        ]
    else:
        environment = None
        parse_command_line = [shell_path, "-n", str(script_path)]

    parsed = subprocess.run(
        parse_command_line,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert parsed.returncode == 0, parsed.stderr
