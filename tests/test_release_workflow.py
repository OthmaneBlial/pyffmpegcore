"""The release workflow validates the remote annotated tag, not checkout's ref alias."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_restores_and_verifies_the_exact_annotated_tag():
    workflow = (REPO_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert "git fetch --force --no-tags origin" in workflow
    assert '"refs/tags/$GITHUB_REF_NAME:refs/tags/$GITHUB_REF_NAME"' in workflow
    assert 'tag --verify "$GITHUB_REF_NAME"' in workflow
    assert 'test "$(git rev-list -n 1 "$GITHUB_REF_NAME")" = "$GITHUB_SHA"' in workflow
