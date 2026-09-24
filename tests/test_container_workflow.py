import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_container_workflow_stays_manual_only():
    workflow = (REPO_ROOT / ".github/workflows/container.yml").read_text(encoding="utf-8")
    trigger_block = workflow.split("\npermissions:\n", maxsplit=1)[0]
    events = re.findall(r"(?m)^  ([a-z][a-z0-9_-]*):(?:\s*(?:#.*)?)?$", trigger_block)

    assert events == ["workflow_dispatch"]
