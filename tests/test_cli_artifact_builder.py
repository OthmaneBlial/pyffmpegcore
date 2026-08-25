"""
Tests for the CLI artifact builder script and distribution docs.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.build_cli_artifacts import validate_sdist_contents

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILDER = REPO_ROOT / "scripts" / "build_cli_artifacts.py"


def test_cli_artifact_builder_help():
    """
    The artifact builder should expose a readable help command.
    """
    result = subprocess.run(
        [sys.executable, str(BUILDER), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Build the supported pyffmpegcore CLI distribution artifacts." in result.stdout
    assert "--outdir" in result.stdout
    assert "--json" in result.stdout


def test_cli_distribution_doc_states_python_packaging_only():
    """
    The distribution doc should keep the current artifact strategy explicit.
    """
    distribution_doc = (REPO_ROOT / "CLI_DISTRIBUTION.md").read_text(encoding="utf-8")
    assert "standard Python packaging only" in distribution_doc
    assert "We are not shipping standalone binaries in this release." in distribution_doc
    assert "self-contained testable source" in distribution_doc


def test_source_distribution_contract_rejects_generated_media(tmp_path):
    import tarfile

    root = tmp_path / "pyffmpegcore-0.0.0"
    generated = root / "tests" / "media" / "downloads"
    generated.mkdir(parents=True)
    (generated / "private.mp4").write_bytes(b"media")
    archive = tmp_path / "pyffmpegcore-0.0.0.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(root, arcname=root.name)

    try:
        validate_sdist_contents(archive)
    except RuntimeError as exc:
        assert "generated or private paths" in str(exc)
    else:  # pragma: no cover - explicit failure message for the contract
        raise AssertionError("generated media must never enter the sdist")
