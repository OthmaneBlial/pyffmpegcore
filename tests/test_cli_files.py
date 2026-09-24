"""
Tests for shared CLI file-handling helpers.
"""

from __future__ import annotations

import pytest

from pyffmpegcore._fileio import open_text_file
from pyffmpegcore.cli_validation import (
    CLIError,
    prepare_output_dir,
    prepare_output_path,
    require_existing_input,
)


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

    with pytest.raises(FileExistsError):
        open_text_file(destination)

    assert destination.read_text(encoding="utf-8") == "concurrent writer"


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
