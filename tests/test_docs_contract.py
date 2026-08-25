"""Contract tests for the local Markdown documentation checker."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from unittest import TestCase

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECK_DOCS = REPO_ROOT / "scripts" / "check_docs.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_docs", CHECK_DOCS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load_checker()


class HeadingSlugTests(TestCase):
    def test_slug_is_lowercase_and_hyphenated(self) -> None:
        self.assertEqual(
            checker.slugify_heading("Install and prove one useful result"),
            "install-and-prove-one-useful-result",
        )

    def test_slug_drops_punctuation(self) -> None:
        self.assertEqual(checker.slugify_heading("What's the plan?"), "whats-the-plan")

    def test_slug_keeps_unicode_letters(self) -> None:
        self.assertEqual(checker.slugify_heading("中文标题"), "中文标题")

    def test_slug_collapses_whitespace(self) -> None:
        self.assertEqual(checker.slugify_heading("  Double   spaced  "), "double-spaced")


class HeadingCollectionTests(TestCase):
    def _markdown(self, content: str) -> Path:
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".md")
        handle.write(content.encode("utf-8"))
        handle.close()
        self.addCleanup(Path(handle.name).unlink)
        return Path(handle.name)

    def test_collects_duplicate_suffixes_deterministically(self) -> None:
        path = self._markdown("# Hello\n## Hello\n## Hello again\n")
        self.assertEqual(
            set(checker.collect_heading_slugs(path)),
            {"hello", "hello-1", "hello-again"},
        )

    def test_skips_heading_inside_code_fence(self) -> None:
        path = self._markdown("```text\n# Not a heading\n```\n# Real heading\n")
        self.assertEqual(set(checker.collect_heading_slugs(path)), {"real-heading"})


class DocumentValidationTests(TestCase):
    def setUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._directory.cleanup)

    def _write(self, name: str, content: str) -> Path:
        path = Path(self._directory.name) / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_valid_fragment_passes(self) -> None:
        guide = self._write("guide.md", "# Missing heading\n")
        source = self._write("source.md", "[link](guide.md#missing-heading)\n")
        self.assertEqual(checker.validate_document(source, source.read_text(encoding="utf-8")), [])

    def test_missing_fragment_fails(self) -> None:
        guide = self._write("guide.md", "# Present heading\n")
        source = self._write("source.md", "[link](guide.md#missing-heading)\n")
        failures = checker.validate_document(source, source.read_text(encoding="utf-8"))
        self.assertEqual(len(failures), 1)
        self.assertIn("missing heading fragment", failures[0])

    def test_same_file_fragment_is_validated(self) -> None:
        source = self._write("source.md", "# Intro\n\n[back](#intro)\n")
        self.assertEqual(checker.validate_document(source, source.read_text(encoding="utf-8")), [])

    def test_missing_file_still_fails(self) -> None:
        source = self._write("source.md", "[link](guide.md)\n")
        failures = checker.validate_document(source, source.read_text(encoding="utf-8"))
        self.assertEqual(len(failures), 1)
        self.assertIn("missing link target", failures[0])

    def test_external_urls_are_not_checked(self) -> None:
        source = self._write("source.md", "[GitHub](https://github.com/example#fragment)\n")
        self.assertEqual(checker.validate_document(source, source.read_text(encoding="utf-8")), [])

    def test_empty_image_alt_still_fails(self) -> None:
        source = self._write("source.md", "![](image.png)\n")
        failures = checker.validate_document(source, source.read_text(encoding="utf-8"))
        self.assertEqual(len(failures), 1)
        self.assertIn("empty alt text", failures[0])

    def test_duplicate_fragment_resolves_to_suffixed_slug(self) -> None:
        guide = self._write("guide.md", "# Duplicate\n## Duplicate\n")
        source = self._write(
            "source.md",
            "# Duplicate\n## Duplicate\n\n[second](#duplicate-1)\n[first](#duplicate)\n",
        )
        self.assertEqual(checker.validate_document(source, source.read_text(encoding="utf-8")), [])

    def test_url_encoded_fragment_is_decoded(self) -> None:
        guide = self._write("guide.md", "# Missing heading\n")
        source = self._write("source.md", "[link](guide.md#missing%20heading)\n")
        self.assertEqual(checker.validate_document(source, source.read_text(encoding="utf-8")), [])
