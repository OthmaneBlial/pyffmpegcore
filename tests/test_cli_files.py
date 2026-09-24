"""
Tests for shared CLI file-handling helpers.
"""

from __future__ import annotations

import json
from argparse import Namespace
from types import SimpleNamespace

import pytest

from pyffmpegcore._fileio import DestinationExistsError, open_text_file
from pyffmpegcore.cli import EXIT_RUNTIME_ERROR, CLIError, handle_batch_run, main
from pyffmpegcore.cli_validation import (
    prepare_output_dir,
    prepare_output_path,
    require_existing_input,
)
from pyffmpegcore.pipeline import PipelineEvent


def test_require_existing_input_rejects_missing_path(tmp_path):
    """
    Input validation should fail early for missing files.
    """
    missing = tmp_path / "missing.mp4"

    with pytest.raises(CLIError) as exc_info:
        require_existing_input(str(missing))

    assert "Input path does not exist" in str(exc_info.value)


def test_prepare_output_path_rejects_existing_file_without_force(tmp_path):
    """
    Output files should not be overwritten silently.
    """
    target = tmp_path / "output.mp4"
    target.write_text("existing", encoding="utf-8")

    with pytest.raises(CLIError) as exc_info:
        prepare_output_path(str(target), force=False)

    assert "--force" in str(exc_info.value)


def test_prepare_output_path_rejects_dangling_symlink_without_force(tmp_path):
    target = tmp_path / "target.json"
    link = tmp_path / "output.json"
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(CLIError, match="Output already exists"):
        prepare_output_path(str(link), force=False)

    assert not target.exists()


def test_open_text_file_does_not_truncate_a_competing_output(tmp_path):
    destination = tmp_path / "events.jsonl"
    destination.write_text("concurrent writer", encoding="utf-8")

    with pytest.raises(DestinationExistsError):
        open_text_file(destination)

    assert destination.read_text(encoding="utf-8") == "concurrent writer"


def test_open_text_file_does_not_label_parent_errors_as_destination_collisions(tmp_path):
    parent = tmp_path / "not-a-directory"
    parent.write_text("block parent creation", encoding="utf-8")

    with pytest.raises(FileExistsError) as error:
        open_text_file(parent / "events.jsonl")

    assert not isinstance(error.value, DestinationExistsError)


def test_prepare_output_path_reports_parent_errors(tmp_path):
    parent = tmp_path / "not-a-directory"
    parent.write_text("block parent creation", encoding="utf-8")

    with pytest.raises(CLIError, match="Unable to prepare output directory") as error:
        prepare_output_path(str(parent / "report.json"), force=False)

    assert error.value.exit_code == 5


def test_batch_event_parent_errors_are_actionable(tmp_path, monkeypatch):
    parent = tmp_path / "not-a-directory"
    parent.write_text("block parent creation", encoding="utf-8")
    args = Namespace(
        verbose=False,
        quiet=False,
        force=False,
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
        receipt=None,
        resume=False,
        dry_run=False,
        explain=False,
        state=None,
        events=parent / "events.jsonl",
        receipt_dir=None,
        result_json=False,
        hash_content=False,
    )
    monkeypatch.setattr(
        "pyffmpegcore.cli_workflows._load_cli_batch", lambda _args: SimpleNamespace(jobs=(), policy=None)
    )
    monkeypatch.setattr(
        "pyffmpegcore.cli_workflows.BatchRunner.run",
        lambda *_args, **_kwargs: pytest.fail("batch must not start when event-log path is invalid"),
    )

    with pytest.raises(CLIError, match="Unable to open events file") as error:
        handle_batch_run(args)

    assert error.value.exit_code == 5


def test_cli_pipeline_event_file_omits_details_when_secrets_are_active(tmp_path, monkeypatch, capsys):
    secret = "integration-secret-never-persist"
    events = tmp_path / "events.jsonl"
    pipeline = SimpleNamespace(
        cache=SimpleNamespace(enabled=False),
        secret_values=(secret,),
        steps=(SimpleNamespace(id="web", plan=SimpleNamespace(outputs=())),),
    )
    result = SimpleNamespace(
        to_dict=lambda: {},
        succeeded=False,
        succeeded_count=0,
        items=(),
    )
    monkeypatch.setattr("pyffmpegcore.cli_workflows._load_cli_pipeline", lambda _args: pipeline)
    monkeypatch.setattr(
        "pyffmpegcore.cli_workflows.PipelinePreflightEngine.prepare",
        lambda *_args, **_kwargs: SimpleNamespace(ok=True, steps=()),
    )

    def run(_runner, _pipeline, **kwargs):
        kwargs["event_callback"](PipelineEvent(1, "failed", "web", secret))
        return result

    monkeypatch.setattr("pyffmpegcore.cli_workflows.PipelineRunner.run", run)

    assert (
        main(["pipeline", "run", str(tmp_path / "pipeline.json"), "--events", str(events), "--result-json"])
        == EXIT_RUNTIME_ERROR
    )
    assert capsys.readouterr().out.strip() == "{}"
    event_text = events.read_text(encoding="utf-8")
    event = json.loads(event_text)
    assert event["detail"] is None
    assert secret not in event_text


def test_prepare_output_path_creates_parent_directories(tmp_path):
    """
    Output helpers should create parent directories for future commands.
    """
    target = tmp_path / "nested" / "output.mp4"

    resolved = prepare_output_path(str(target), force=False)

    assert resolved == target
    assert target.parent.exists()


def test_prepare_output_dir_rejects_non_empty_directory_without_force(tmp_path):
    """
    Directory-based workflows should not reuse populated output folders silently.
    """
    output_dir = tmp_path / "images"
    output_dir.mkdir()
    (output_dir / "existing.txt").write_text("present", encoding="utf-8")

    with pytest.raises(CLIError) as exc_info:
        prepare_output_dir(str(output_dir), force=False)

    assert "not empty" in str(exc_info.value)


def test_prepare_output_dir_accepts_non_empty_directory_with_force(tmp_path):
    """
    Force mode should permit reuse of an existing output directory.
    """
    output_dir = tmp_path / "images"
    output_dir.mkdir()
    (output_dir / "existing.txt").write_text("present", encoding="utf-8")

    resolved = prepare_output_dir(str(output_dir), force=True)

    assert resolved == output_dir
