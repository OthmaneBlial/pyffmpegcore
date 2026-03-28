"""
Build the supported CLI distribution artifacts and report their metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def sha256_for_file(path: Path) -> str:
    """
    Compute the SHA256 digest for a file.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_artifacts(project_root: Path, outdir: Path) -> subprocess.CompletedProcess[str]:
    """
    Build the wheel and sdist artifacts into the requested output directory.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--sdist",
            "--wheel",
            "--outdir",
            str(outdir),
        ],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        check=False,
    )


def collect_artifact_report(outdir: Path) -> dict[str, object]:
    """
    Collect metadata for the built wheel and sdist artifacts.
    """
    artifacts = []
    for artifact in sorted(outdir.glob("pyffmpegcore-*")):
        if artifact.suffix not in {".whl", ".gz"}:
            continue
        artifacts.append(
            {
                "filename": artifact.name,
                "path": str(artifact),
                "size_bytes": artifact.stat().st_size,
                "sha256": sha256_for_file(artifact),
                "type": "wheel" if artifact.suffix == ".whl" else "sdist",
            }
        )

    return {
        "distribution_strategy": "python-packaging-only",
        "standalone_binaries": False,
        "artifacts": artifacts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the supported pyffmpegcore CLI distribution artifacts."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root to build from. Defaults to %(default)s.",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=REPO_ROOT / "dist",
        help="Output directory for built artifacts. Defaults to %(default)s.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the artifact report as JSON.",
    )
    args = parser.parse_args(argv)

    build_result = build_artifacts(args.project_root, args.outdir)
    if build_result.returncode != 0:
        sys.stderr.write(build_result.stderr or build_result.stdout)
        return build_result.returncode

    report = collect_artifact_report(args.outdir)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("Distribution strategy: python-packaging-only")
        print("Standalone binaries: no")
        for artifact in report["artifacts"]:
            print(
                f"{artifact['type']}: {artifact['filename']} "
                f"({artifact['size_bytes']} bytes, sha256={artifact['sha256']})"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
