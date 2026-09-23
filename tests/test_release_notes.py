"""Release notes remain versioned, reviewable, and free of stale placeholders."""

from pathlib import Path

import pytest

from scripts.render_release_notes import render_release_notes

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_v022_release_notes_link_exact_recipes_proof_and_compatibility():
    template = (REPO_ROOT / ".github/release-notes/v0.2.2.md").read_text(encoding="utf-8")

    rendered = render_release_notes(
        template,
        tag="v0.2.2",
        run_url="https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/123",
    )

    assert "{{" not in rendered
    assert "v0.2.2" in rendered
    assert "/terminal-demo/" in rendered
    assert "/recipes/web-video/" in rendered
    assert "/recipes/exact-size/" in rendered
    assert "/recipes/podcast/" in rendered
    assert "/recipes/preserve-streams/" in rendered
    assert "/evidence/" in rendered
    assert "/COMPATIBILITY/" in rendered
    assert "/actions/runs/123" in rendered
    assert "Problems this release addresses" in rendered


def test_v030_release_notes_describe_verified_output_contracts():
    template = (REPO_ROOT / ".github/release-notes/v0.3.0.md").read_text(encoding="utf-8")

    rendered = render_release_notes(
        template,
        tag="v0.3.0",
        run_url="https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/456",
    )

    assert "{{" not in rendered
    assert "v0.3.0" in rendered
    assert "/actions/runs/456" in rendered
    assert "FFprobe" in rendered
    assert "do not decode every packet or frame" in rendered
    assert "subtitle language" in rendered
    assert "Historical synthetic recipe evidence from public `0.2.2`" in rendered


def test_release_notes_reject_unknown_placeholders():
    with pytest.raises(ValueError, match="unresolved"):
        render_release_notes(
            "Release {{ unknown }}",
            tag="v0.2.2",
            run_url="https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/123",
        )
