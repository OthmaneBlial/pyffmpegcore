# CLI Platform Notes

This file records the honest platform expectations for the `pyffmpegcore` CLI.

## Shared Rules

- `ffmpeg` and `ffprobe` must be installed separately.
- `pipx` is the cleanest install path for most CLI users.
- `python -m pip install --user pyffmpegcore` may require a new shell before the command appears on `PATH`.
- Paths with spaces are part of the clean-install smoke checks.

## Linux And macOS

- `install.sh` is the one-command bootstrap path.
- `pipx install pyffmpegcore` is the preferred packaging path.
- The local March 28, 2026 validation was deepest on Linux.

## Windows

- Do not use `install.sh`.
- Use `install.ps1` or a direct `pipx` or `pip` install from PowerShell.
- The console script may appear as `pyffmpegcore.exe`.

## Clean-Install Validator

The repository now includes a reusable validator:

```bash
python scripts/validate_cli_install.py
```

What it checks:

- build a fresh wheel
- create a clean virtual environment
- install the wheel into that environment
- run `pyffmpegcore --version`
- run `pyffmpegcore doctor --json`
- run a small real-media smoke pass unless `--skip-media` is used

This validator is meant to run on Linux, macOS, and Windows CI runners.
