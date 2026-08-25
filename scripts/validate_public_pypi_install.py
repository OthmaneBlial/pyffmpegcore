"""Install one public PyPI release with pipx and prove its essential CLI path."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def cli_path(bin_dir: Path, *, platform: str | None = None) -> Path:
    """Resolve the console-script filename for the current runner platform."""
    platform = platform or os.name
    suffix = ".exe" if platform == "nt" else ""
    return bin_dir / f"pyffmpegcore{suffix}"


def run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a public CLI command and retain readable failure evidence."""
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    print(f"$ {' '.join(command)}")
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"command exited with {result.returncode}: {command!r}")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Release version or v-prefixed tag.")
    parser.add_argument("--bin-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    version = args.version.removeprefix("v")
    args.bin_dir.mkdir(parents=True, exist_ok=True)
    run_checked([sys.executable, "-m", "pipx", "install", f"pyffmpegcore=={version}"])

    executable = cli_path(args.bin_dir)
    if not executable.is_file():
        parser.error(f"pipx did not create the expected console script: {executable}")

    version_result = run_checked([str(executable), "--version"])
    if version_result.stdout.strip() != f"pyffmpegcore {version}":
        parser.error(f"unexpected version output: {version_result.stdout!r}")

    run_checked([str(executable), "doctor"])
    with tempfile.TemporaryDirectory(prefix="pyffmpegcore-public-smoke-") as smoke_dir:
        run_checked([str(executable), "smoke-test", "--keep-dir", str(Path(smoke_dir) / "media")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
