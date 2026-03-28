"""
Validate a clean CLI install in an isolated virtual environment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEDIA_ROOT = REPO_ROOT / "tests" / "media" / "downloads"
DOWNLOADER = REPO_ROOT / "tests" / "media" / "download_fixtures.py"


def run_command(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """
    Run a subprocess and capture output for reporting.
    """
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )


def venv_python(venv_dir: Path) -> Path:
    """
    Return the Python executable path for a virtual environment.
    """
    if sys.platform.startswith("win"):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def venv_cli(venv_dir: Path) -> Path:
    """
    Return the pyffmpegcore console-script path for a virtual environment.
    """
    if sys.platform.startswith("win"):
        return venv_dir / "Scripts" / "pyffmpegcore.exe"
    return venv_dir / "bin" / "pyffmpegcore"


def ensure_media(media_root: Path) -> None:
    """
    Ensure the real-media fixtures are present before running media checks.
    """
    required = [
        media_root / "sample_mp4_h264.mp4",
        media_root / "sample_webm_vp9.webm",
        media_root / "sample_audio_mp3.mp3",
    ]
    if all(path.exists() for path in required):
        return

    result = run_command([sys.executable, str(DOWNLOADER)], cwd=REPO_ROOT)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "Fixture download failed.")


def add_report_entry(
    report: list[dict[str, object]],
    name: str,
    result: subprocess.CompletedProcess[str],
) -> None:
    """
    Append a compact command result to the report list.
    """
    report.append(
        {
            "name": name,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a clean pyffmpegcore CLI install in an isolated virtual environment."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root used for building the wheel. Defaults to %(default)s.",
    )
    parser.add_argument(
        "--media-root",
        type=Path,
        default=DEFAULT_MEDIA_ROOT,
        help="Directory containing downloaded media fixtures. Defaults to %(default)s.",
    )
    parser.add_argument(
        "--skip-media",
        action="store_true",
        help="Skip the real-media smoke commands after install.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the validation summary as JSON.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep the temporary validation workspace for debugging.",
    )
    args = parser.parse_args(argv)

    workspace = Path(tempfile.mkdtemp(prefix="pyffmpegcore-clean-install-"))
    report: dict[str, object] = {"workspace": str(workspace), "commands": []}

    try:
        build_dir = workspace / "dist"
        venv_dir = workspace / "venv"
        outputs_dir = workspace / "outputs with spaces"
        build_dir.mkdir(parents=True, exist_ok=True)
        outputs_dir.mkdir(parents=True, exist_ok=True)

        build = run_command(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(build_dir)],
            cwd=args.project_root,
        )
        add_report_entry(report["commands"], "build-wheel", build)
        if build.returncode != 0:
            return 1

        wheels = sorted(build_dir.glob("pyffmpegcore-*.whl"))
        if not wheels:
            raise RuntimeError("No wheel was produced during clean-install validation.")
        wheel_path = wheels[-1]

        create_venv = run_command([sys.executable, "-m", "venv", str(venv_dir)])
        add_report_entry(report["commands"], "create-venv", create_venv)
        if create_venv.returncode != 0:
            return 1

        python_path = venv_python(venv_dir)
        cli_path = venv_cli(venv_dir)

        upgrade_pip = run_command([str(python_path), "-m", "pip", "install", "--upgrade", "pip"])
        add_report_entry(report["commands"], "upgrade-pip", upgrade_pip)
        if upgrade_pip.returncode != 0:
            return 1

        install = run_command([str(python_path), "-m", "pip", "install", str(wheel_path)])
        add_report_entry(report["commands"], "install-wheel", install)
        if install.returncode != 0:
            return 1

        version = run_command([str(cli_path), "--version"])
        add_report_entry(report["commands"], "cli-version", version)
        if version.returncode != 0:
            return 1

        doctor = run_command([str(cli_path), "doctor", "--json"])
        add_report_entry(report["commands"], "cli-doctor", doctor)
        if doctor.returncode != 0:
            return 1

        if not args.skip_media:
            ensure_media(args.media_root)

            probe = run_command(
                [
                    str(cli_path),
                    "probe",
                    "--input",
                    str(args.media_root / "sample_mp4_h264.mp4"),
                    "--json",
                ]
            )
            add_report_entry(report["commands"], "probe-json", probe)
            if probe.returncode != 0:
                return 1

            convert_output = outputs_dir / "converted clip.mp4"
            convert = run_command(
                [
                    str(cli_path),
                    "convert",
                    "--input",
                    str(args.media_root / "sample_webm_vp9.webm"),
                    "--output",
                    str(convert_output),
                    "--video-codec",
                    "libx264",
                    "--audio-codec",
                    "aac",
                ]
            )
            add_report_entry(report["commands"], "convert", convert)
            if convert.returncode != 0 or not convert_output.exists():
                return 1

            audio_output = outputs_dir / "audio clip.mp3"
            extract = run_command(
                [
                    str(cli_path),
                    "extract-audio",
                    "--input",
                    str(args.media_root / "sample_mp4_h264.mp4"),
                    "--output",
                    str(audio_output),
                ]
            )
            add_report_entry(report["commands"], "extract-audio", extract)
            if extract.returncode != 0 or not audio_output.exists():
                return 1

            thumb_output = outputs_dir / "thumb one.jpg"
            thumbnail = run_command(
                [
                    str(cli_path),
                    "thumbnail",
                    "--input",
                    str(args.media_root / "sample_mp4_h264.mp4"),
                    "--output",
                    str(thumb_output),
                    "--timestamp",
                    "00:00:01",
                    "--width",
                    "640",
                ]
            )
            add_report_entry(report["commands"], "thumbnail", thumbnail)
            if thumbnail.returncode != 0 or not thumb_output.exists():
                return 1

        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"Clean install validation workspace: {workspace}")
            for entry in report["commands"]:
                print(f"{entry['name']}: rc={entry['returncode']}")

        return 0
    finally:
        if not args.keep_temp:
            shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
