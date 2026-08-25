"""Check local Markdown links, image alternatives, heading fragments, and unsafe install claims."""

from __future__ import annotations

import re
import sys
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_ROOTS = [REPO_ROOT / "README.md", *sorted((REPO_ROOT / "docs").rglob("*.md"))]
LINK_PATTERN = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")
IMAGE_PATTERN = re.compile(r"!\[([^]]*)\]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^#{1,6}[ \t]+(.*)$")
FENCE_PATTERN = re.compile(r"^[ \t]*(```|~~~)")
INVALID_SLUG_CHARS = re.compile(r"[^\w\- ]", re.UNICODE)
WHITESPACE_RUN = re.compile(r"\s+")


def slugify_heading(text: str) -> str:
    """Return the GitHub/MkDocs-style anchor for a Markdown heading."""
    slug = WHITESPACE_RUN.sub("-", INVALID_SLUG_CHARS.sub("", text.strip().lower()))
    return slug.strip("-")


@lru_cache(maxsize=None)
def collect_heading_slugs(path: Path) -> frozenset[str]:
    """Return heading anchors for a Markdown file, including duplicate suffixes."""
    slugs: set[str] = set()
    counts: dict[str, int] = {}
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE_PATTERN.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_PATTERN.match(line)
        if match is None:
            continue
        base = slugify_heading(match.group(1))
        if not base:
            continue
        ordinal = counts.get(base, 0)
        counts[base] = ordinal + 1
        slugs.add(base if ordinal == 0 else f"{base}-{ordinal}")
    return frozenset(slugs)


def parse_local_target(source: Path, target: str) -> tuple[Path | None, str | None]:
    """Split a Markdown target into a local path and optional heading fragment."""
    if target.startswith(("http://", "https://", "mailto:")):
        return None, None
    path_part, separator, fragment = target.partition("#")
    path_part = path_part.strip()
    if not path_part:
        return (source, unquote(fragment.strip())) if separator and fragment.strip() else (None, None)
    return (source.parent / path_part).resolve(), unquote(fragment.strip()) if separator else None


def _describe(source: Path) -> Path:
    try:
        return source.relative_to(REPO_ROOT)
    except ValueError:
        return source


def validate_document(source: Path, text: str) -> list[str]:
    """Validate links, image alternatives, and heading fragments in one document."""
    failures = []
    for target in LINK_PATTERN.findall(text):
        resolved, fragment = parse_local_target(source, target)
        if resolved is None:
            continue
        if not resolved.exists():
            failures.append(f"{_describe(source)}: missing link target {target}")
            continue
        if (
            fragment is not None
            and resolved.is_file()
            and slugify_heading(fragment) not in collect_heading_slugs(resolved)
        ):
            failures.append(f"{_describe(source)}: missing heading fragment {target}")
    for alternative, target in IMAGE_PATTERN.findall(text):
        if not alternative.strip():
            failures.append(f"{_describe(source)}: image {target} has empty alt text")
    return failures


def main() -> int:
    failures = []
    for source in DOC_ROOTS:
        failures.extend(validate_document(source, source.read_text(encoding="utf-8")))

    if "python -m pip install pyffmpegcore" in (REPO_ROOT / "README.md").read_text(encoding="utf-8"):
        failures.append("README.md: advertises PyPI before the public endpoint is verified")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
