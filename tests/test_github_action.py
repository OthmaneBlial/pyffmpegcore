"""Contracts for the immutable, secret-safe composite pipeline Action."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ACTION_SCRIPT = REPO_ROOT / "scripts" / "run_pipeline_action.sh"


def _action_environment(workspace: Path, image: str) -> dict[str, str]:
    return {
        **os.environ,
        "GITHUB_WORKSPACE": str(workspace),
        "PYFFMPEGCORE_ACTION_IMAGE": image,
        "PYFFMPEGCORE_ACTION_PIPELINE": "pipeline.json",
        "PYFFMPEGCORE_ACTION_RECEIPT_DIR": ".pyffmpegcore/receipts",
        "PYFFMPEGCORE_ACTION_STATE": ".pyffmpegcore/state.json",
        "PYFFMPEGCORE_ACTION_EVENTS": ".pyffmpegcore/events.jsonl",
        "PYFFMPEGCORE_ACTION_RESULT": ".pyffmpegcore/result.json",
        "PYFFMPEGCORE_ACTION_VARIABLES": "API_TOKEN",
        "PYFFMPEGCORE_ACTION_RESUME": "true",
        "PYFFMPEGCORE_ACTION_FORCE": "true",
        "PYFFMPEGCORE_ACTION_NETWORK": "none",
        "API_TOKEN": "must-never-appear-in-arguments",
    }


def test_action_script_passes_only_secret_names_to_pinned_container(tmp_path):
    workspace = tmp_path / "workspace"
    fake_bin = tmp_path / "bin"
    workspace.mkdir()
    fake_bin.mkdir()
    (workspace / "pipeline.json").write_text('{"schema_version":"1.0"}\n', encoding="utf-8")
    argument_log = tmp_path / "docker-arguments.txt"
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        '#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$DOCKER_ARGUMENT_LOG"\nprintf \'{"schema_version":"1.0"}\\n\'\n',
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)
    digest = "a" * 64
    environment = _action_environment(workspace, f"ghcr.io/othmaneblial/pyffmpegcore@sha256:{digest}")
    environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
    environment["DOCKER_ARGUMENT_LOG"] = str(argument_log)

    result = subprocess.run(["bash", str(ACTION_SCRIPT)], env=environment, capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
    arguments = argument_log.read_text(encoding="utf-8").splitlines()
    assert f"ghcr.io/othmaneblial/pyffmpegcore@sha256:{digest}" in arguments
    assert "--network" in arguments and "none" in arguments
    assert "--env" in arguments and "API_TOKEN" in arguments
    assert "--var" in arguments and "--resume" in arguments and "--force" in arguments
    assert "must-never-appear-in-arguments" not in arguments
    assert (workspace / ".pyffmpegcore" / "result.json").is_file()


def test_action_script_rejects_mutable_image_and_parent_paths(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "pipeline.json").write_text("{}\n", encoding="utf-8")
    mutable = _action_environment(workspace, "ghcr.io/othmaneblial/pyffmpegcore:edge")
    result = subprocess.run(["bash", str(ACTION_SCRIPT)], env=mutable, capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert "pinned by sha256 digest" in result.stderr

    escaped = _action_environment(workspace, f"ghcr.io/othmaneblial/pyffmpegcore@sha256:{'b' * 64}")
    escaped["PYFFMPEGCORE_ACTION_PIPELINE"] = "../pipeline.json"
    result = subprocess.run(["bash", str(ACTION_SCRIPT)], env=escaped, capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert "stay inside GITHUB_WORKSPACE" in result.stderr


@pytest.mark.parametrize(
    ("setting", "relative_path"),
    [
        ("PYFFMPEGCORE_ACTION_PIPELINE", "escape/pipeline.json"),
        ("PYFFMPEGCORE_ACTION_RECEIPT_DIR", "escape/receipts"),
        ("PYFFMPEGCORE_ACTION_STATE", "escape/state.json"),
        ("PYFFMPEGCORE_ACTION_EVENTS", "escape/events.jsonl"),
        ("PYFFMPEGCORE_ACTION_RESULT", "escape/result.json"),
        ("PYFFMPEGCORE_ACTION_ARTIFACTS", "escape/**"),
    ],
)
def test_action_script_rejects_workspace_symlink_escape(tmp_path, setting, relative_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (workspace / "pipeline.json").write_text("{}\n", encoding="utf-8")
    try:
        (workspace / "escape").symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("creating a directory symlink is unavailable on this host")
    environment = _action_environment(workspace, f"ghcr.io/othmaneblial/pyffmpegcore@sha256:{'b' * 64}")
    environment[setting] = relative_path

    result = subprocess.run(["bash", str(ACTION_SCRIPT)], env=environment, capture_output=True, text=True, check=False)

    assert result.returncode == 2
    assert "symbolic link" in result.stderr
    assert list(outside.iterdir()) == []


def test_action_path_validation_accepts_unicode_and_spaces_without_docker(tmp_path):
    workspace = tmp_path / "workspace"
    source_dir = workspace / "média été"
    output_dir = workspace / "sorties été"
    source_dir.mkdir(parents=True)
    output_dir.mkdir()
    (source_dir / "pipeline.json").write_text("{}\n", encoding="utf-8")
    environment = _action_environment(workspace, f"ghcr.io/othmaneblial/pyffmpegcore@sha256:{'c' * 64}")
    environment["PYFFMPEGCORE_ACTION_PIPELINE"] = "média été/pipeline.json"
    environment["PYFFMPEGCORE_ACTION_ARTIFACTS"] = "sorties été/**"

    result = subprocess.run(
        ["bash", str(ACTION_SCRIPT), "--validate-only"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_action_metadata_uses_immutable_image_and_pinned_dependencies():
    metadata = (REPO_ROOT / "action.yml").read_text(encoding="utf-8")
    digest_match = re.search(r"ghcr\.io/othmaneblial/pyffmpegcore@sha256:([0-9a-f]{64})", metadata)
    assert digest_match is not None
    assert set(digest_match.group(1)) != {"0"}
    assert digest_match.group(1) == "0244808caf90485eb7cf9fe99d7505b8739b90587fc8aab9ae412126e964a12c"
    integration_workflow = (REPO_ROOT / ".github" / "workflows" / "action-integration.yml").read_text(encoding="utf-8")
    assert f"ghcr.io/othmaneblial/pyffmpegcore@sha256:{digest_match.group(1)}" in integration_workflow
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in metadata
    assert "include-hidden-files: true" in metadata
