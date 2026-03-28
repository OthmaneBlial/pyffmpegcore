"""
Smoke tests for the root CLI entrypoint.
"""

from __future__ import annotations

import subprocess
import sys

from pyffmpegcore import __version__


def test_cli_root_help_smoke():
    """
    The module entrypoint should print root help and exit cleanly.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "usage: pyffmpegcore" in result.stdout
    assert "--verbose" in result.stdout
    assert "--quiet" in result.stdout


def test_cli_version_smoke():
    """
    The module entrypoint should expose the package version.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == f"pyffmpegcore {__version__}"


def test_cli_rejects_verbose_and_quiet_together():
    """
    Global verbosity flags should remain mutually exclusive.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pyffmpegcore", "--verbose", "--quiet"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "not allowed with argument" in result.stderr
