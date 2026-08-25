#!/usr/bin/env python3
"""Benchmark PyFFmpegCore startup, processing, artifact, and pipeline-cache overhead."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import statistics
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str], *, cwd: Path | None = None) -> tuple[float, subprocess.CompletedProcess[str]]:
    started = time.perf_counter()
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    elapsed = time.perf_counter() - started
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {command}\n{result.stderr or result.stdout}")
    return elapsed, result


def _median(command: list[str], repeats: int, *, cwd: Path | None = None) -> float:
    samples = [_run(command, cwd=cwd)[0] for _ in range(repeats)]
    return statistics.median(samples)


def _directory_size(path: Path) -> int:
    return sum(
        item.stat().st_size
        for item in path.rglob("*")
        if item.is_file() and "__pycache__" not in item.parts and item.suffix not in {".pyc", ".pyo"}
    )


def _version_line(command: list[str]) -> str:
    result = _run(command)[1]
    return (result.stdout or result.stderr).splitlines()[0]


def benchmark(args: argparse.Namespace) -> dict[str, Any]:
    cli_candidate = Path(args.cli)
    ffmpeg_candidate = Path(args.ffmpeg)
    cli_path = str(cli_candidate.resolve()) if cli_candidate.exists() else shutil.which(args.cli) or args.cli
    ffmpeg_path = (
        str(ffmpeg_candidate.resolve()) if ffmpeg_candidate.exists() else shutil.which(args.ffmpeg) or args.ffmpeg
    )
    with tempfile.TemporaryDirectory(prefix="pyffmpegcore-benchmark-") as temp_dir:
        workspace = Path(temp_dir)
        source = workspace / "source.mp4"
        _run(
            [
                ffmpeg_path,
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=640x360:rate=24",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=660:sample_rate=44100",
                "-t",
                "2",
                "-c:v",
                "mpeg4",
                "-q:v",
                "8",
                "-c:a",
                "aac",
                "-pix_fmt",
                "yuv420p",
                "-shortest",
                "-y",
                str(source),
            ]
        )

        raw_output = workspace / "raw.jpg"
        cli_output = workspace / "cli.jpg"
        _, preview = _run(
            [
                cli_path,
                "thumbnail",
                "--input",
                str(source),
                "--output",
                str(cli_output),
                "--timestamp",
                "00:00:00.100",
                "--width",
                "320",
                "--force",
                "--dry-run",
                "--plan-json",
                "--ffmpeg-path",
                ffmpeg_path,
            ]
        )
        planned_command = json.loads(preview.stdout)["plan"]["command"]
        raw_command = [*planned_command[:-1], str(raw_output)]
        cli_command = [
            cli_path,
            "thumbnail",
            "--input",
            str(source),
            "--output",
            str(cli_output),
            "--timestamp",
            "00:00:00.100",
            "--width",
            "320",
            "--force",
            "--quiet",
            "--ffmpeg-path",
            ffmpeg_path,
        ]
        _run(raw_command)
        _run(cli_command)
        raw_processing = _median(raw_command, args.repeats)
        cli_processing = _median(cli_command, args.repeats)

        pipeline_path = workspace / "cache-pipeline.json"
        pipeline_output = workspace / "cached.mp4"
        pipeline_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "name": "benchmark_cache",
                    "cache": {"enabled": True, "directory": ".cache", "content_aware": True},
                    "steps": [
                        {
                            "id": "web",
                            "profile": "web/mp4-compatible",
                            "input": str(source),
                            "output": str(pipeline_output),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        pipeline_command = [
            cli_path,
            "pipeline",
            "run",
            str(pipeline_path),
            "--result-json",
            "--ffmpeg-path",
            ffmpeg_path,
        ]
        cache_cold, cold_result = _run(pipeline_command, cwd=workspace)
        cache_warm, warm_result = _run(pipeline_command, cwd=workspace)
        cold_status = json.loads(cold_result.stdout)["items"][0]["status"]
        warm_status = json.loads(warm_result.stdout)["items"][0]["status"]

        ffmpeg_startup = _median([ffmpeg_path, "-version"], args.repeats)
        cli_startup = _median([cli_path, "--version"], args.repeats)
        processing_overhead = cli_processing - raw_processing
        startup_overhead = cli_startup - ffmpeg_startup
        wheel_size = args.wheel.stat().st_size if args.wheel is not None else None
        report: dict[str, Any] = {
            "schema_version": "1.0",
            "environment": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "ffmpeg": _version_line([ffmpeg_path, "-version"]),
                "cli": _version_line([cli_path, "--version"]),
                "repeats": args.repeats,
            },
            "startup": {
                "raw_ffmpeg_median_seconds": round(ffmpeg_startup, 6),
                "pyffmpegcore_median_seconds": round(cli_startup, 6),
                "orchestration_overhead_seconds": round(startup_overhead, 6),
            },
            "processing": {
                "workflow": "thumbnail",
                "raw_exact_plan_median_seconds": round(raw_processing, 6),
                "pyffmpegcore_median_seconds": round(cli_processing, 6),
                "orchestration_overhead_seconds": round(processing_overhead, 6),
                "raw_output_bytes": raw_output.stat().st_size,
                "pyffmpegcore_output_bytes": cli_output.stat().st_size,
            },
            "cache": {
                "cold_seconds": round(cache_cold, 6),
                "warm_seconds": round(cache_warm, 6),
                "cold_status": cold_status,
                "warm_status": warm_status,
                "speedup": round(cache_cold / cache_warm, 3) if cache_warm else None,
            },
            "artifacts": {
                "wheel_bytes": wheel_size,
                "package_source_bytes": _directory_size(REPO_ROOT / "pyffmpegcore"),
            },
            "thresholds": {
                "startup_overhead_max_seconds": args.max_startup_overhead,
                "processing_overhead_max_seconds": args.max_processing_overhead,
                "startup_pass": startup_overhead <= args.max_startup_overhead,
                "processing_pass": processing_overhead <= args.max_processing_overhead,
                "cache_pass": warm_status == "cached" and cache_warm < cache_cold,
            },
        }
        report["passed"] = all(report["thresholds"][key] for key in ("startup_pass", "processing_pass", "cache_pass"))
        return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cli", default="pyffmpegcore", help="Installed CLI path or command name.")
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg path or command name.")
    parser.add_argument("--wheel", type=Path, help="Optional wheel whose byte size should be recorded.")
    parser.add_argument("--repeats", type=int, default=5, help="Median sample count. Defaults to %(default)s.")
    parser.add_argument("--max-startup-overhead", type=float, default=0.5)
    parser.add_argument("--max-processing-overhead", type=float, default=1.0)
    parser.add_argument("--output", type=Path, help="Optional JSON report path.")
    parser.add_argument("--strict", action="store_true", help="Fail when an overhead/cache threshold is missed.")
    args = parser.parse_args(argv)
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    report = benchmark(args)
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 1 if args.strict and not report["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
