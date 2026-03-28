"""
Repository-level sanity checks.
"""

from __future__ import annotations

import importlib.util
import py_compile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_FILES = sorted((REPO_ROOT / "pyffmpegcore").glob("*.py"))
TEST_FILES = sorted((REPO_ROOT / "tests").glob("test_*.py"))
EXAMPLE_FILES = sorted((REPO_ROOT / "examples").glob("*.py"))

# Phase 4 removes this quarantine once the example is repaired.
QUARANTINED_EXAMPLES = {"adjust_video_speed.py"}


def _load_module_from_path(path: Path) -> None:
    module_name = path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def test_python_sources_compile() -> None:
    for path in [*PACKAGE_FILES, *TEST_FILES]:
        py_compile.compile(str(path), doraise=True)

    for path in EXAMPLE_FILES:
        if path.name not in QUARANTINED_EXAMPLES:
            py_compile.compile(str(path), doraise=True)


def test_example_modules_import_cleanly() -> None:
    for path in EXAMPLE_FILES:
        if path.name not in QUARANTINED_EXAMPLES:
            _load_module_from_path(path)
