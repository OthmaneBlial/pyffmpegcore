#!/usr/bin/env python3
"""
Download and verify internet-backed media fixtures.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST = SCRIPT_DIR / "manifest.json"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "downloads"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temp_handle:
        temp_path = Path(temp_handle.name)

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "pyffmpegcore-fixture-downloader/1.0",
                "Accept": "*/*",
            },
        )
        with urllib.request.urlopen(request) as response, temp_path.open("wb") as output:
            shutil.copyfileobj(response, output)
        temp_path.replace(destination)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def ensure_fixture(output_dir: Path, fixture: dict, force: bool) -> None:
    destination = output_dir / fixture["filename"]
    expected_sha = fixture["sha256"]

    if destination.exists() and not force:
        actual_sha = sha256_file(destination)
        if actual_sha == expected_sha:
            print(f"[ok] {fixture['filename']} already verified")
            return
        print(f"[stale] {fixture['filename']} checksum mismatch, re-downloading")

    print(f"[download] {fixture['filename']} <- {fixture['url']}")
    download_file(fixture["url"], destination)

    actual_sha = sha256_file(destination)
    if actual_sha != expected_sha:
        destination.unlink(missing_ok=True)
        raise RuntimeError(
            f"Checksum mismatch for {fixture['filename']}: "
            f"expected {expected_sha}, got {actual_sha}"
        )

    print(f"[verified] {fixture['filename']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--force", action="store_true", help="re-download every fixture")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    fixtures = manifest.get("fixtures", [])
    if not fixtures:
        raise RuntimeError(f"No fixtures defined in {args.manifest}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for fixture in fixtures:
        ensure_fixture(args.output_dir, fixture, args.force)

    print(f"Downloaded and verified {len(fixtures)} fixtures into {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
