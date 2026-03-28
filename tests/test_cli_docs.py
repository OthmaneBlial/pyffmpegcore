"""
Tests for CLI-first public documentation.
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_readme_is_cli_first():
    """
    The README should lead with the CLI install and command flow.
    """
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "PyFFmpegCore is now designed to be used first as a CLI" in readme
    assert "pipx install pyffmpegcore" in readme
    assert "pyffmpegcore doctor" in readme
    assert "## Python API" in readme


def test_examples_markdown_is_command_oriented():
    """
    The examples guide should now document terminal commands with real sample files.
    """
    examples = (REPO_ROOT / "EXAMPLES.md").read_text(encoding="utf-8")
    assert "# CLI Examples" in examples
    assert "pyffmpegcore subtitles burn" in examples
    assert "tests/media/downloads/sample_webm_vp9.webm" in examples
    assert "Replace the sample input path with your own file" in examples
