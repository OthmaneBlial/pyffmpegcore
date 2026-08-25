"""
Build the supported CLI distribution artifacts and report their metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
from pathlib import Path

from pyffmpegcore import __version__

REPO_ROOT = Path(__file__).resolve().parents[1]

SDIST_ALLOWED_ROOT_ENTRIES = frozenset(
    {
        "CHANGELOG.md",
        "CLI_BETA_CHECKLIST.md",
        "CLI_DISTRIBUTION.md",
        "CLI_HELP.md",
        "CLI_INSTALL.md",
        "CLI_PLATFORM_NOTES.md",
        "CLI_SPEC.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "DEVELOPMENT.md",
        "EXAMPLES.md",
        "LICENSE",
        "MANIFEST.in",
        "PKG-INFO",
        "README.md",
        "RELEASE_CHECKLIST.md",
        "ROADMAP.md",
        "SECURITY.md",
        "SUPPORT.md",
        "docs",
        "examples",
        "install.ps1",
        "install.sh",
        "pyffmpegcore",
        "pyffmpegcore.egg-info",
        "pyproject.toml",
        "scripts",
        "setup.cfg",
        "tests",
    }
)
SDIST_REQUIRED_PATHS = frozenset(
    {
        "LICENSE",
        "README.md",
        "docs/schemas/run-receipt-1.0.example.json",
        "docs/schemas/run-receipt-1.0.schema.json",
        "docs/schemas/batch-manifest-1.0.example.json",
        "docs/schemas/batch-manifest-1.0.schema.json",
        "pyproject.toml",
        "pyffmpegcore/__init__.py",
        "pyffmpegcore/batch.py",
        "pyffmpegcore/cli.py",
        "scripts/build_cli_artifacts.py",
        "scripts/validate_capability_catalog.py",
        "tests/media/download_fixtures.py",
        "tests/media/manifest.json",
    }
)
SDIST_FORBIDDEN_PARTS = frozenset({".git", ".venv", "dist", "downloads", "site", "__pycache__"})


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


def validate_sdist_contents(path: Path) -> dict[str, object]:
    """Enforce the self-contained, testable source-artifact contract."""
    with tarfile.open(path, "r:gz") as archive:
        member_paths = [Path(member.name) for member in archive.getmembers()]

    roots = {parts[0] for member in member_paths if (parts := member.parts)}
    if len(roots) != 1:
        raise RuntimeError(f"sdist must contain exactly one root directory, got {sorted(roots)!r}")

    root = next(iter(roots))
    relative_paths = [Path(*member.parts[1:]) for member in member_paths if len(member.parts) > 1]
    unsafe = [str(path) for path in relative_paths if path.is_absolute() or ".." in path.parts]
    if unsafe:
        raise RuntimeError(f"sdist contains unsafe paths: {unsafe!r}")

    forbidden = sorted(str(path) for path in relative_paths if SDIST_FORBIDDEN_PARTS.intersection(path.parts))
    if forbidden:
        raise RuntimeError(f"sdist contains generated or private paths: {forbidden!r}")

    actual_top_entries = {path.parts[0] for path in relative_paths if path.parts}
    unexpected = sorted(actual_top_entries - SDIST_ALLOWED_ROOT_ENTRIES)
    missing_top = sorted(SDIST_ALLOWED_ROOT_ENTRIES - actual_top_entries)
    if unexpected or missing_top:
        raise RuntimeError(f"sdist top-level contract mismatch: unexpected={unexpected!r}, missing={missing_top!r}")

    names = {path.as_posix() for path in relative_paths}
    missing_required = sorted(SDIST_REQUIRED_PATHS - names)
    if missing_required:
        raise RuntimeError(f"sdist is missing required source/test paths: {missing_required!r}")

    return {
        "schema_version": "1.0",
        "strategy": "self-contained-testable-source",
        "root": root,
        "file_count": len(names),
        "required_paths": sorted(SDIST_REQUIRED_PATHS),
        "forbidden_parts": sorted(SDIST_FORBIDDEN_PARTS),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the supported pyffmpegcore CLI distribution artifacts.")
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
    sdist_path = args.outdir / f"pyffmpegcore-{__version__}.tar.gz"
    try:
        report["sdist_contract"] = validate_sdist_contents(sdist_path)
    except (OSError, RuntimeError, tarfile.TarError) as exc:
        print(f"Source distribution contract failed: {exc}", file=sys.stderr)
        return 1
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
