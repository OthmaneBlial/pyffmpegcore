# CLI Platform Notes

This file records the honest platform expectations for the `pyffmpegcore` CLI.

## Shared Rules

- Python 3.10 through 3.14 is the maintained package range.
- `ffmpeg` and `ffprobe` must be installed separately.
- `pipx` is the cleanest install path for most CLI users.
- user-level `pip` installs may require a new shell before the command appears on `PATH`.
- Paths with spaces are part of the clean-install smoke checks.

## Linux And macOS

- `install.sh` is the one-command bootstrap path.
- `pipx install "pyffmpegcore==0.2.2"` is the validated public PyPI path.
- Current platform proof lives in CI rather than a dated local claim.

## Windows

- Do not use `install.sh`.
- Use `install.ps1` or a direct `pipx` or `pip` install from PowerShell.
- The console script may appear as `pyffmpegcore.exe`.

## Clean-Install Validator

The repository now includes a reusable validator:

```bash
python scripts/validate_cli_install.py
```

By default it builds a wheel locally. Release and compatibility jobs instead pass `--artifact dist/` so every platform tests the exact same prebuilt wheel. It checks:

- build a fresh wheel or select exactly one supplied wheel
- create a clean virtual environment
- install the wheel into that environment
- run `pyffmpegcore --version`
- run `pyffmpegcore doctor --json`
- run a small real-media smoke pass unless `--skip-media` is used

The required compatibility matrix runs it on Linux, macOS, and Windows with Python 3.10 and 3.14. Intermediate Python versions run the package contract on Linux. See [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) for the tested-versus-expected policy.
