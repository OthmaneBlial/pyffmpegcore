"""Cross-platform contracts for generated-media fixture metadata."""

from __future__ import annotations

import json
from pathlib import Path

from tests import media_utils


def test_manifest_is_utf8_even_when_windows_default_is_cp1252(tmp_path, monkeypatch) -> None:
    payload = {"fixtures": [{"id": "smart-quote-\u201d"}]}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    original_read_text = Path.read_text

    def read_with_windows_default(path: Path, encoding: str | None = None, errors: str | None = None) -> str:
        return original_read_text(path, encoding=encoding or "cp1252", errors=errors)

    monkeypatch.setattr(media_utils, "MANIFEST_PATH", manifest)
    monkeypatch.setattr(Path, "read_text", read_with_windows_default)
    media_utils.load_manifest.cache_clear()
    try:
        assert media_utils.load_manifest() == payload
    finally:
        media_utils.load_manifest.cache_clear()
