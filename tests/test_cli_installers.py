"""
Tests for the one-command installer scripts.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SHELL_INSTALLER = REPO_ROOT / "install.sh"
POWERSHELL_INSTALLER = REPO_ROOT / "install.ps1"


def test_shell_installer_help_and_syntax():
    """
    The Linux/macOS installer should be syntax-valid and explain its options.
    """
    syntax_result = subprocess.run(
        ["bash", "-n", str(SHELL_INSTALLER)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert syntax_result.returncode == 0

    help_result = subprocess.run(
        ["bash", str(SHELL_INSTALLER), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert help_result.returncode == 0
    assert "Install PyFFmpegCore as a terminal command on Linux or macOS." in help_result.stdout
    assert "--method auto|pipx|pip" in help_result.stdout


def test_powershell_installer_contains_expected_install_paths():
    """
    The Windows installer should document pipx and pip user installs.
    """
    script = POWERSHELL_INSTALLER.read_text(encoding="utf-8")
    assert 'ValidateSet("Auto", "Pipx", "Pip")' in script
    assert "pipx install --force" in script
    assert "-m pip install --user --upgrade" in script


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="PowerShell is not installed")
def test_powershell_installer_help():
    """
    The Windows installer should expose a readable help mode when PowerShell is available.
    """
    result = subprocess.run(
        ["pwsh", "-NoLogo", "-NoProfile", "-File", str(POWERSHELL_INSTALLER), "-Help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Install PyFFmpegCore as a terminal command on Windows." in result.stdout
