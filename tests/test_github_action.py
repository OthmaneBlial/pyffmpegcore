"""Contracts for the immutable, secret-safe composite pipeline Action."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

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


def test_action_metadata_uses_immutable_image_and_pinned_dependencies():
    metadata = (REPO_ROOT / "action.yml").read_text(encoding="utf-8")
    digest_match = re.search(r"ghcr\.io/othmaneblial/pyffmpegcore@sha256:([0-9a-f]{64})", metadata)
    assert digest_match is not None
    assert set(digest_match.group(1)) != {"0"}
    assert digest_match.group(1) == "b2ec3d7ffc054ce65a5e3470e4ffb19d15708d30e613c01e3217bb9331251458"
    assert "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02" in metadata
    assert "include-hidden-files: true" in metadata
