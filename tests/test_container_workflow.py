import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _events(name: str) -> list[str]:
    workflow = (REPO_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
    trigger_block = workflow.split("\npermissions:\n", maxsplit=1)[0]
    return re.findall(r"(?m)^  ([a-z][a-z0-9_-]*):(?:\s*(?:#.*)?)?$", trigger_block)


def test_container_workflow_stays_manual_only():
    assert _events("container.yml") == ["workflow_dispatch"]


@pytest.mark.parametrize(
    ("workflow", "expected"),
    [
        ("ci.yml", ["pull_request", "workflow_dispatch"]),
        ("benchmark.yml", ["pull_request", "workflow_dispatch"]),
        ("fixtures.yml", ["workflow_dispatch"]),
        ("action-integration.yml", ["workflow_dispatch"]),
    ],
)
def test_heavy_workflows_have_no_push_or_scheduled_trigger(workflow, expected):
    assert _events(workflow) == expected
