"""
Tests for the clean-install validation script.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = REPO_ROOT / "scripts" / "validate_cli_install.py"


def test_clean_install_validator_help():
    """
    The clean-install validator should expose a readable CLI.
    """
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Validate a clean pyffmpegcore CLI install" in result.stdout
    assert "--skip-media" in result.stdout
    assert "--keep-temp" in result.stdout
