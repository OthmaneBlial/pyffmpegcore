"""
Tests for the clean-install validation script.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.validate_cli_install import doctor_result_is_acceptable, run_command

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
    assert "--artifact" in result.stdout
    assert "--skip-media" in result.stdout
    assert "--keep-temp" in result.stdout


def test_no_media_contract_accepts_structured_missing_binary_report():
    result = subprocess.CompletedProcess(
        ["pyffmpegcore", "doctor", "--json"],
        3,
        '{"cli_version":"0.2.0","ffmpeg":{"available":false},"ffprobe":{"available":false}}',
        "",
    )

    assert doctor_result_is_acceptable(result, require_binaries=False)
    assert not doctor_result_is_acceptable(result, require_binaries=True)


def test_no_media_contract_rejects_invalid_doctor_output():
    result = subprocess.CompletedProcess(["pyffmpegcore", "doctor", "--json"], 3, "not-json", "")

    assert not doctor_result_is_acceptable(result, require_binaries=False)


def test_clean_install_commands_are_observable_and_bounded(capsys):
    result = run_command(
        [sys.executable, "-c", "import time; time.sleep(1)"],
        label="intentional-timeout",
        timeout_seconds=0.01,
    )

    assert result.returncode == 124
    assert "Command timed out after 0.01 seconds." in result.stderr
    captured = capsys.readouterr()
    assert "starting intentional-timeout" in captured.err
    assert "failed intentional-timeout (rc=124)" in captured.err
