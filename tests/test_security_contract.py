"""Security invariants for runtime command execution."""

from __future__ import annotations

import ast
from pathlib import Path

RUNTIME_ROOT = Path(__file__).resolve().parents[1] / "pyffmpegcore"
PROCESS_FUNCTIONS = {"run", "Popen", "call", "check_call", "check_output"}


def test_runtime_never_invokes_a_shell():
    """Runtime subprocess calls must preserve argument-array semantics."""
    for source_path in RUNTIME_ROOT.glob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert "os.system(" not in source
        assert "create_subprocess_shell(" not in source

        tree = ast.parse(source, filename=str(source_path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in PROCESS_FUNCTIONS:
                continue
            if not isinstance(node.func.value, ast.Name) or node.func.value.id != "subprocess":
                continue

            shell_keywords = [keyword for keyword in node.keywords if keyword.arg == "shell"]
            assert all(keyword.value is not ast.Constant or keyword.value.value is False for keyword in shell_keywords)
            assert node.args, f"{source_path}:{node.lineno} subprocess call has no command argument"
            assert not isinstance(node.args[0], (ast.Constant, ast.JoinedStr, ast.BinOp)), (
                f"{source_path}:{node.lineno} must pass an argument array, not a command string"
            )
