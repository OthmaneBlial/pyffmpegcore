"""
Tests for the one-command installer scripts.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SHELL_INSTALLER = REPO_ROOT / "install.sh"
POWERSHELL_INSTALLER = REPO_ROOT / "install.ps1"
VERSION_TEXT = (REPO_ROOT / "pyffmpegcore" / "__init__.py").read_text(encoding="utf-8")
VERSION_MATCH = re.search(r'^__version__ = "([^"]+)"$', VERSION_TEXT, re.MULTILINE)
assert VERSION_MATCH is not None
CURRENT_VERSION = VERSION_MATCH.group(1)
CURRENT_PACKAGE_SPEC = f"pyffmpegcore=={CURRENT_VERSION}"


def test_public_install_guidance_uses_source_version():
    """Current install examples stay aligned with the package version source."""
    shell_installer = SHELL_INSTALLER.read_text(encoding="utf-8")
    assert f'PACKAGE_SPEC="${{PYFFMPEGCORE_PACKAGE_SPEC:-{CURRENT_PACKAGE_SPEC}}}"' in shell_installer
    powershell_installer = POWERSHELL_INSTALLER.read_text(encoding="utf-8")
    assert f'return "{CURRENT_PACKAGE_SPEC}"' in powershell_installer

    for relative_path in (
        "CLI_BETA_CHECKLIST.md",
        "CLI_DISTRIBUTION.md",
        "CLI_INSTALL.md",
        "CLI_PLATFORM_NOTES.md",
        "README.md",
        "docs/installation.md",
        "docs/quickstart.md",
        "docs/index.md",
    ):
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert CURRENT_PACKAGE_SPEC in text, relative_path


def test_linux_ffmpeg_install_guidance_checks_both_binaries_and_workflow():
    """Distribution instructions must include package provenance and executable checks."""
    installation = (REPO_ROOT / "docs" / "installation.md").read_text(encoding="utf-8")
    assert "sudo dnf install ffmpeg-free" in installation
    assert "sudo pacman -S ffmpeg" in installation
    assert "packages.fedoraproject.org/pkgs/ffmpeg/ffmpeg-free/" in installation
    assert "archlinux.org/packages/extra/x86_64/ffmpeg/" in installation
    for command in ("ffmpeg -version", "ffprobe -version", "pyffmpegcore doctor", "pyffmpegcore smoke-test"):
        assert command in installation
    assert "not executed on those distributions" in installation


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
    assert f"Defaults to the public {CURRENT_VERSION} release." in help_result.stdout


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
