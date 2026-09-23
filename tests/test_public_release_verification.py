"""The post-publication gate requires the exact wheel and source release."""

import subprocess
from pathlib import Path
from unittest.mock import patch

from scripts.validate_public_pypi_install import cli_path, run_checked
from scripts.wait_for_pypi import expected_filenames, release_filenames


def test_expected_pypi_release_requires_wheel_and_sdist():
    expected = expected_filenames("0.2.0")

    assert expected == {
        "pyffmpegcore-0.2.0-py3-none-any.whl",
        "pyffmpegcore-0.2.0.tar.gz",
    }
    assert (
        release_filenames(
            {
                "releases": {
                    "0.2.0": [
                        {"filename": "pyffmpegcore-0.2.0-py3-none-any.whl"},
                        {"filename": "pyffmpegcore-0.2.0.tar.gz"},
                    ]
                }
            },
            "0.2.0",
        )
        == expected
    )


def test_release_filename_parser_rejects_malformed_payloads():
    assert release_filenames({}, "0.2.0") == set()
    assert release_filenames({"releases": []}, "0.2.0") == set()
    assert release_filenames({"releases": {"0.2.0": {}}}, "0.2.0") == set()


def test_public_console_script_path_is_platform_specific():
    bin_dir = Path("pipx-bin")

    assert cli_path(bin_dir, platform="posix") == bin_dir / "pyffmpegcore"
    assert cli_path(bin_dir, platform="nt") == bin_dir / "pyffmpegcore.exe"


@patch("scripts.validate_public_pypi_install.subprocess.run")
def test_public_install_command_decodes_tool_output_as_utf8(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(["pyffmpegcore"], 0, "ok", "")

    run_checked(["pyffmpegcore", "--version"])

    assert mock_run.call_args.kwargs["encoding"] == "utf-8"
    assert mock_run.call_args.kwargs["errors"] == "replace"
