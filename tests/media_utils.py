"""
Helpers for internet-backed media fixtures used in real integration tests.
"""

from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MEDIA_ROOT = REPO_ROOT / "tests" / "media"
MANIFEST_PATH = MEDIA_ROOT / "manifest.json"
DOWNLOADS_DIR = MEDIA_ROOT / "downloads"
DOWNLOADER = MEDIA_ROOT / "download_fixtures.py"


@lru_cache(maxsize=1)
def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


@lru_cache(maxsize=1)
def ensure_downloaded_media() -> dict[str, Path]:
    manifest = load_manifest()
    fixture_map = {
        fixture["id"]: DOWNLOADS_DIR / fixture["filename"]
        for fixture in manifest["fixtures"]
    }

    if any(not path.exists() for path in fixture_map.values()):
        subprocess.run(
            [sys.executable, str(DOWNLOADER)],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    return fixture_map
