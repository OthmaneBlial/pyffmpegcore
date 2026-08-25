"""Render release notes from a versioned, reviewable template."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*[^{}]+\s*\}\}")


def render_release_notes(template: str, *, tag: str, run_url: str) -> str:
    """Replace the bounded release placeholders and reject template drift."""
    rendered = template.replace("{{ tag }}", tag).replace("{{ release_run_url }}", run_url)
    unresolved = sorted(set(PLACEHOLDER_PATTERN.findall(rendered)))
    if unresolved:
        raise ValueError(f"unresolved release-note placeholders: {unresolved!r}")
    return rendered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args(argv)

    if not args.tag.startswith("v"):
        parser.error("--tag must start with 'v'")
    if not args.run_url.startswith("https://github.com/"):
        parser.error("--run-url must be an HTTPS GitHub URL")

    try:
        template = args.template.read_text(encoding="utf-8")
        rendered = render_release_notes(template, tag=args.tag, run_url=args.run_url)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
