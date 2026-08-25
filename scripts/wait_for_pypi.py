"""Wait for an exact pyffmpegcore release to become public on PyPI."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request

PYPI_JSON_URL = "https://pypi.org/pypi/pyffmpegcore/json"


def expected_filenames(version: str) -> set[str]:
    """Return the exact distribution filenames produced by the release build."""
    return {
        f"pyffmpegcore-{version}-py3-none-any.whl",
        f"pyffmpegcore-{version}.tar.gz",
    }


def release_filenames(payload: dict[str, object], version: str) -> set[str]:
    """Read filenames for one version from a PyPI JSON response."""
    releases = payload.get("releases")
    if not isinstance(releases, dict):
        return set()
    files = releases.get(version)
    if not isinstance(files, list):
        return set()
    return {
        filename for item in files if isinstance(item, dict) and isinstance((filename := item.get("filename")), str)
    }


def fetch_pypi_payload() -> dict[str, object]:
    """Fetch public package metadata without credentials."""
    request = urllib.request.Request(
        PYPI_JSON_URL,
        headers={"Accept": "application/json", "User-Agent": "pyffmpegcore-release-verifier/1.0"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("PyPI returned a non-object JSON document")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Release version or v-prefixed tag.")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--interval", type=float, default=10.0)
    args = parser.parse_args(argv)

    version = args.version.removeprefix("v")
    expected = expected_filenames(version)
    deadline = time.monotonic() + args.timeout
    last_detail = "no response received"

    while time.monotonic() < deadline:
        try:
            payload = fetch_pypi_payload()
            actual = release_filenames(payload, version)
            missing = sorted(expected - actual)
            if not missing:
                print(f"PyPI release {version} is public with: {', '.join(sorted(actual))}")
                return 0
            last_detail = f"missing files: {missing!r}"
        except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as exc:
            last_detail = str(exc)
        time.sleep(args.interval)

    parser.error(f"PyPI release {version} did not become ready before timeout: {last_detail}")


if __name__ == "__main__":
    raise SystemExit(main())
