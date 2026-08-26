"""Check local Markdown links, image alternatives, and unsafe install claims."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_ROOTS = [
    *sorted(REPO_ROOT.glob("*.md")),
    *sorted((REPO_ROOT / "docs").rglob("*.md")),
]
LINK_PATTERN = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")
IMAGE_PATTERN = re.compile(r"!\[([^]]*)\]\(([^)]+)\)")


HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)


def slugify_heading(text: str) -> str:
    """Convert heading text to GitHub/MkDocs-compatible anchor slug."""
    import unicodedata
    text = unicodedata.normalize("NFKD", text).lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-{2,}", "-", text)
    return text


def extract_headings(path: Path) -> dict[str, int]:
    """Return mapping of slug -> count for all headings in a Markdown file."""
    text = path.read_text(encoding="utf-8")
    slugs: dict[str, int] = {}
    for match in HEADING_PATTERN.finditer(text):
        slug = slugify_heading(match.group(1))
        slugs[slug] = slugs.get(slug, 0) + 1
    return slugs


def resolve_local_link(source: Path, target: str) -> tuple[Path | None, str | None]:
    """Resolve a Markdown target, returning (path, fragment) or (None, None) for external."""
    parts = target.split("#", 1)
    file_part = parts[0].strip()
    fragment = parts[1].strip() if len(parts) > 1 else None
    if not file_part or file_part.startswith(("http://", "https://", "mailto:")):
        return None, None
    resolved = (source.parent / file_part).resolve()
    return resolved, fragment


def main() -> int:
    failures = []
    for source in DOC_ROOTS:
        text = source.read_text(encoding="utf-8")
        for target in LINK_PATTERN.findall(text):
            resolved, fragment = resolve_local_link(source, target)
            if resolved is not None and not resolved.exists():
                failures.append(f"{source.relative_to(REPO_ROOT)}: missing link target {target}")
            elif resolved is not None and resolved.exists() and fragment is not None:
                headings = extract_headings(resolved)
                if fragment not in headings:
                    failures.append(f"{source.relative_to(REPO_ROOT)}: missing heading fragment #{fragment} in {target.split('#')[0]}")
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
