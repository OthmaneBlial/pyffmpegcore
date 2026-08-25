"""Check local Markdown links, image alternatives, and unsafe install claims."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_ROOTS = [REPO_ROOT / "README.md", *sorted((REPO_ROOT / "docs").rglob("*.md"))]
LINK_PATTERN = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")
IMAGE_PATTERN = re.compile(r"!\[([^]]*)\]\(([^)]+)\)")


def resolve_local_link(source: Path, target: str) -> Path | None:
    """Resolve a Markdown target when it points to a local file."""
    target = target.split("#", 1)[0].strip()
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None
    return (source.parent / target).resolve()


def main() -> int:
    failures = []
    for source in DOC_ROOTS:
        text = source.read_text(encoding="utf-8")
        for target in LINK_PATTERN.findall(text):
            resolved = resolve_local_link(source, target)
            if resolved is not None and not resolved.exists():
                failures.append(f"{source.relative_to(REPO_ROOT)}: missing link target {target}")
        for alternative, target in IMAGE_PATTERN.findall(text):
            if not alternative.strip():
                failures.append(f"{source.relative_to(REPO_ROOT)}: image {target} has empty alt text")

    if "python -m pip install pyffmpegcore" in (REPO_ROOT / "README.md").read_text(encoding="utf-8"):
        failures.append("README.md: advertises PyPI before the public endpoint is verified")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
