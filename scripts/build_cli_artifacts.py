"""
Build the supported CLI distribution artifacts and report their metadata.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import cast

from pyffmpegcore import __version__

REPO_ROOT = Path(__file__).resolve().parents[1]

SDIST_ALLOWED_ROOT_ENTRIES = frozenset(
    {
        "CHANGELOG.md",
        "action.yml",
        "benchmarks",
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
        "fuzz",
        "LICENSE",
        "MANIFEST.in",
        "PKG-INFO",
        "README.md",
        "RELEASE_CHECKLIST.md",
        "ROADMAP.md",
        "SECURITY.md",
        "SECURITY_TRIAGE.md",
        "SUPPORT.md",
        "docs",
        "examples",
        "install.ps1",
        "install.sh",
        "LAUNCH.md",
        "pipelines",
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
        "action.yml",
        "docs/schemas/run-receipt-1.0.example.json",
        "docs/schemas/run-receipt-1.0.schema.json",
        "docs/schemas/batch-manifest-1.0.example.json",
        "docs/schemas/batch-manifest-1.0.schema.json",
        "docs/schemas/batch-manifest-1.1.example.json",
        "docs/schemas/batch-manifest-1.1.schema.json",
        "docs/schemas/pipeline-1.0.schema.json",
        "pyproject.toml",
        "pyffmpegcore/__init__.py",
        "pyffmpegcore/batch.py",
        "pyffmpegcore/pipeline.py",
        "pipelines/podcast-package.toml",
        "pipelines/video-thumbnails-subtitles.json",
        "pipelines/web-publish.json",
        "benchmarks/baseline-macos-arm64-2026-08-25.json",
        "pyffmpegcore/cli.py",
        "scripts/build_cli_artifacts.py",
        "scripts/run_pipeline_action.sh",
        "scripts/validate_capability_catalog.py",
        "tests/media/download_fixtures.py",
        "tests/media/manifest.json",
        "fuzz/corpus/receipt/valid.json",
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


def resolve_source_date_epoch(project_root: Path) -> int | None:
    """Use an explicit epoch, the source commit time, or the sdist metadata time."""
    configured = os.environ.get("SOURCE_DATE_EPOCH")
    if configured is not None:
        value = configured.strip()
        if not value.isascii() or not value.isdigit():
            raise ValueError("SOURCE_DATE_EPOCH must be a non-negative integer")
        epoch = int(value)
        if epoch > 0xFFFFFFFF:
            raise ValueError("SOURCE_DATE_EPOCH must not exceed 4294967295 for gzip timestamps")
        return epoch

    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        result = None
    if result is not None and result.returncode == 0:
        value = result.stdout.strip()
        if value.isascii() and value.isdigit():
            return int(value)

    sdist_metadata = project_root / "PKG-INFO"
    if sdist_metadata.is_file():
        return int(sdist_metadata.stat().st_mtime)
    return None


def normalize_sdist(path: Path, source_date_epoch: int) -> None:
    """Normalize tar metadata so the same sdist source produces identical bytes."""
    file_mode = path.stat().st_mode
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as raw:
            temporary_path = Path(raw.name)
            with tarfile.open(path, "r:gz") as source:
                members = sorted(source.getmembers(), key=lambda member: member.name)
                with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=source_date_epoch) as compressed:
                    with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as target:
                        for member in members:
                            normalized = copy.copy(member)
                            normalized.mtime = source_date_epoch
                            normalized.uid = normalized.gid = 0
                            normalized.uname = normalized.gname = ""
                            normalized.pax_headers = {
                                key: value
                                for key, value in sorted(member.pax_headers.items())
                                if key not in {"atime", "ctime", "mtime"}
                            }
                            source_file = source.extractfile(member) if member.isfile() else None
                            if member.isfile() and source_file is None:
                                raise RuntimeError(f"could not read sdist member: {member.name}")
                            target.addfile(normalized, source_file)
                            if source_file is not None:
                                source_file.close()
        os.chmod(temporary_path, file_mode & 0o7777)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def build_artifacts(
    project_root: Path,
    outdir: Path,
    source_date_epoch: int | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Build the wheel and sdist artifacts into the requested output directory.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    if source_date_epoch is not None:
        environment["SOURCE_DATE_EPOCH"] = str(source_date_epoch)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--sdist",
            "--wheel",
            "--outdir",
            str(outdir),
        ],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=environment,
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

    try:
        source_date_epoch = resolve_source_date_epoch(args.project_root)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    build_result = build_artifacts(args.project_root, args.outdir, source_date_epoch)
    if build_result.returncode != 0:
        sys.stderr.write(build_result.stderr or build_result.stdout)
        return build_result.returncode

    sdist_path = args.outdir / f"pyffmpegcore-{__version__}.tar.gz"
    try:
        if source_date_epoch is not None:
            normalize_sdist(sdist_path, source_date_epoch)
        sdist_contract = validate_sdist_contents(sdist_path)
    except (OSError, RuntimeError, tarfile.TarError) as exc:
        print(f"Source distribution contract failed: {exc}", file=sys.stderr)
        return 1
    report = collect_artifact_report(args.outdir)
    report["sdist_contract"] = sdist_contract
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("Distribution strategy: python-packaging-only")
        print("Standalone binaries: no")
        for artifact in cast(list[dict[str, object]], report["artifacts"]):
            print(
                f"{artifact['type']}: {artifact['filename']} "
                f"({artifact['size_bytes']} bytes, sha256={artifact['sha256']})"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
