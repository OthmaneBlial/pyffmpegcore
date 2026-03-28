"""
Tests for installed CLI packaging behavior.
"""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from pathlib import Path


def test_console_script_entry_point_is_registered():
    """
    The installed package should register the pyffmpegcore console script.
    """
    entry_points = importlib.metadata.entry_points(group="console_scripts")
    mapping = {entry_point.name: entry_point.value for entry_point in entry_points}
    assert mapping["pyffmpegcore"] == "pyffmpegcore.cli:main"


def test_installed_console_script_runs_version():
    """
    The installed console script should be invokable directly.
    """
    script = Path(sys.executable).with_name("pyffmpegcore")
    assert script.exists()

    result = subprocess.run(
        [str(script), "--version"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip().startswith("pyffmpegcore ")
