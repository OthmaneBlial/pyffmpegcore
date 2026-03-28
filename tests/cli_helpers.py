"""
Helpers for invoking the installed pyffmpegcore console script in tests.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def installed_cli_path() -> Path:
    """
    Return the installed console-script path for the active Python environment.
    """
    scripts_dir = Path(sys.executable).parent
    candidates = [
        scripts_dir / "pyffmpegcore",
        scripts_dir / "pyffmpegcore.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Installed pyffmpegcore console script was not found.")


def run_installed_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """
    Run the installed console script and capture its output.
    """
    command = [str(installed_cli_path()), *args]
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )
