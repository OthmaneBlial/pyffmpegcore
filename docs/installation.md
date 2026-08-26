# Installation

## Requirements

- Python 3.10–3.14
- `ffmpeg` and `ffprobe` on `PATH`, or explicit binary paths
- `pipx` for the recommended isolated CLI install

Install FFmpeg using the package source you already trust for your operating system. PyFFmpegCore deliberately does not download or bundle it.

## Bash or zsh

Install the exact validated public release:

```bash
pipx install "pyffmpegcore==0.2.2"
pyffmpegcore --version
pyffmpegcore doctor
pyffmpegcore smoke-test
```

A repository checkout also provides `./install.sh`.

`uv` users can install the same release as an isolated tool:

```bash
uv tool install "pyffmpegcore==0.2.2"
pyffmpegcore smoke-test
```

## PowerShell

```powershell
pipx install "pyffmpegcore==0.2.2"
pyffmpegcore --version
pyffmpegcore doctor
pyffmpegcore smoke-test
```

From a checkout, use `./install.ps1`; do not run the POSIX shell installer on Windows.

## Python project dependency

For a Python project dependency:

```bash
python -m pip install "pyffmpegcore==0.2.2"
```

Use an appropriate compatible-release constraint after validating future
versions against your own media workflows.

There is no Homebrew tap today. The project will add and maintain one only after
public demand justifies another release channel; Homebrew can still install the
external FFmpeg dependency.

## Verify the selected binaries

```bash
pyffmpegcore doctor --json
```

The report includes resolved paths, versions, build configuration, capability counts, selected workflow encoders/filters, and hardware accelerators. Supplying an untrusted `--ffmpeg-path` or `--ffprobe-path` executes that binary; treat it like any other executable.
