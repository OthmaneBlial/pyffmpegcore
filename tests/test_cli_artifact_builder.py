"""
Tests for the CLI artifact builder script and distribution docs.
"""

from __future__ import annotations

import subprocess
import sys
import tarfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from scripts.build_cli_artifacts import (
    build_artifacts,
    normalize_sdist,
    resolve_source_date_epoch,
    validate_sdist_contents,
)

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


@patch("scripts.build_cli_artifacts.subprocess.run")
def test_build_artifacts_decodes_tool_output_as_utf8(mock_run, tmp_path):
    mock_run.return_value = subprocess.CompletedProcess(["python", "-m", "build"], 0, "", "")

    build_artifacts(REPO_ROOT, tmp_path / "dist", source_date_epoch=1234567890)

    assert mock_run.call_args.kwargs["encoding"] == "utf-8"
    assert mock_run.call_args.kwargs["errors"] == "replace"
    assert mock_run.call_args.kwargs["env"]["SOURCE_DATE_EPOCH"] == "1234567890"


def test_resolve_source_date_epoch_uses_commit_time_or_sdist_metadata(monkeypatch, tmp_path):
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    metadata = tmp_path / "PKG-INFO"
    metadata.write_text("metadata", encoding="utf-8")
    metadata.touch()
    metadata_epoch = int(metadata.stat().st_mtime)

    with patch("scripts.build_cli_artifacts.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess(["git"], 0, "1790206849\n", "")
        assert resolve_source_date_epoch(tmp_path) == 1790206849
        run.return_value = subprocess.CompletedProcess(["git"], 128, "", "not a repository")
        assert resolve_source_date_epoch(tmp_path) == metadata_epoch


def test_resolve_source_date_epoch_rejects_invalid_environment_value(monkeypatch, tmp_path):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "yesterday")

    try:
        resolve_source_date_epoch(tmp_path)
    except ValueError as exc:
        assert "non-negative integer" in str(exc)
    else:  # pragma: no cover - explicit failure message for the contract
        raise AssertionError("invalid SOURCE_DATE_EPOCH must be rejected")


def test_resolve_source_date_epoch_rejects_value_outside_gzip_range(monkeypatch, tmp_path):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "4294967296")

    try:
        resolve_source_date_epoch(tmp_path)
    except ValueError as exc:
        assert "gzip timestamps" in str(exc)
    else:  # pragma: no cover - explicit failure message for the contract
        raise AssertionError("out-of-range SOURCE_DATE_EPOCH must be rejected")


def test_normalize_sdist_makes_tar_metadata_reproducible(tmp_path):
    archives = [tmp_path / "first.tar.gz", tmp_path / "second.tar.gz"]
    for archive, source_mtime in zip(archives, (100, 200), strict=True):
        with tarfile.open(archive, "w:gz") as output:
            member = tarfile.TarInfo("package/file.txt")
            member.size = len(b"stable contents")
            member.mtime = source_mtime
            member.uid = source_mtime
            member.gid = source_mtime
            output.addfile(member, BytesIO(b"stable contents"))
        normalize_sdist(archive, source_date_epoch=1234567890)

    assert archives[0].read_bytes() == archives[1].read_bytes()
    with tarfile.open(archives[0], "r:gz") as normalized:
        member = normalized.getmember("package/file.txt")
        assert member.mtime == 1234567890
        assert member.uid == 0
        assert member.gid == 0
        assert normalized.extractfile(member).read() == b"stable contents"


def test_cli_distribution_doc_distinguishes_release_artifacts_from_integrations():
    """
    The distribution doc should keep the current artifact strategy explicit.
    """
    distribution_doc = (REPO_ROOT / "CLI_DISTRIBUTION.md").read_text(encoding="utf-8")
    assert "wheel and sdist remain the downloadable Python release artifacts" in distribution_doc
    assert "digest-pinned container image" in distribution_doc
    assert "GitHub Action" in distribution_doc
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
