"""Versioned built-in and local profile contracts."""

from __future__ import annotations

import json

import pytest

from pyffmpegcore import ProfileRegistry, ValidationError, WorkflowPlanner
from tests.cli_helpers import run_installed_cli


def test_builtin_registry_contains_the_five_task_profiles():
    registry = ProfileRegistry()

    names = {profile.name for profile in registry.list()}

    assert names == {
        "archive/mezzanine",
        "audio/podcast-speech",
        "subtitles/accessibility",
        "web/mp4-compatible",
        "web/small-upload",
    }
    assert registry.get("web/mp4-compatible").profile_version == 1


def test_json_and_toml_profiles_use_the_same_strict_schema(tmp_path):
    payload = {
        "schema_version": "1.0",
        "name": "project/review-copy",
        "profile_version": 1,
        "description": "Small review copy",
        "workflow": "convert",
        "options": {"video_codec": "libx264", "crf": 30},
        "required_capabilities": ["encoder:libx264"],
    }
    json_path = tmp_path / "review.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    toml_path = tmp_path / "review.toml"
    toml_path.write_text(
        "\n".join(
            [
                'schema_version = "1.0"',
                'name = "project/review-copy"',
                "profile_version = 1",
                'description = "Small review copy"',
                'workflow = "convert"',
                'required_capabilities = ["encoder:libx264"]',
                "[options]",
                'video_codec = "libx264"',
                "crf = 30",
            ]
        ),
        encoding="utf-8",
    )
    registry = ProfileRegistry()

    assert registry.load_file(json_path).to_dict() == registry.load_file(toml_path).to_dict()


def test_profile_schema_rejects_unknown_fields(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "name": "project/unsafe",
                "profile_version": 1,
                "description": "Invalid",
                "workflow": "convert",
                "options": {},
                "raw_shell": "ffmpeg $(secret)",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="Unknown profile fields: raw_shell"):
        ProfileRegistry().load_file(path)


def test_profile_cli_lists_shows_and_validates(tmp_path):
    listed = run_installed_cli("profile", "list", "--json")
    shown = run_installed_cli("profile", "show", "web/mp4-compatible", "--json")
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "name": "user/local-web",
                "profile_version": 1,
                "description": "Local web output",
                "workflow": "convert",
                "options": {"video_codec": "libx264"},
            }
        ),
        encoding="utf-8",
    )
    validated = run_installed_cli("profile", "validate", str(profile_path), "--json")

    assert listed.returncode == 0
    assert len(json.loads(listed.stdout)["profiles"]) == 5
    assert shown.returncode == 0
    assert json.loads(shown.stdout)["name"] == "web/mp4-compatible"
    assert validated.returncode == 0
    assert json.loads(validated.stdout)["valid"] is True


def test_builtin_profile_compiles_through_shared_typed_planner(tmp_path):
    plan = ProfileRegistry().plan(
        "web/mp4-compatible",
        WorkflowPlanner(),
        str(tmp_path / "input.webm"),
        str(tmp_path / "output.mp4"),
    )

    assert plan.workflow == "convert"
    assert plan.metadata["profile"] == {
        "schema_version": "1.0",
        "name": "web/mp4-compatible",
        "profile_version": 1,
    }
    assert "encoder:libx264" in plan.required_capabilities
    assert plan.operations[0] == "apply profile web/mp4-compatible v1"


def test_builtin_profile_rejects_an_output_that_breaks_its_contract(tmp_path):
    with pytest.raises(ValidationError, match="requires an output extension"):
        ProfileRegistry().plan(
            "archive/mezzanine",
            WorkflowPlanner(),
            str(tmp_path / "input.mp4"),
            str(tmp_path / "output.mp4"),
        )
