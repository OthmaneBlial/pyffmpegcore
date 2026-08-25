"""
Helpers for locally generated media fixtures used in real integration tests.
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


@lru_cache(maxsize=None)
def ffmpeg_has_filter(filter_name: str, ffmpeg_path: str = "ffmpeg") -> bool:
    """Return whether the local FFmpeg build exposes a named filter."""
    result = subprocess.run(
        [ffmpeg_path, "-hide_banner", "-filters"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    return any(
        line.split()[1:2] == [filter_name]
        for line in result.stdout.splitlines()
        if line.strip() and not line.lstrip().startswith("Filters:")
    )


@lru_cache(maxsize=None)
def ffmpeg_has_encoder(encoder_name: str, ffmpeg_path: str = "ffmpeg") -> bool:
    """Return whether the local FFmpeg build exposes a named encoder."""
    result = subprocess.run(
        [ffmpeg_path, "-hide_banner", "-encoders"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    return any(
        line.split()[1:2] == [encoder_name]
        for line in result.stdout.splitlines()
        if line.strip() and not line.lstrip().startswith("Encoders:")
    )


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

    subprocess.run(
        [sys.executable, str(DOWNLOADER)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    return fixture_map
