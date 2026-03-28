# CLI Installation

This project now ships a `pyffmpegcore` console command.

## Requirements

- Python `3.8+`
- `ffmpeg`
- `ffprobe`

Install FFmpeg first using your normal OS package manager or binary installer.

## Install With `pipx`

`pipx` is the cleanest option for most CLI users because it installs the app in an isolated environment but still exposes the command globally.

```bash
pipx install pyffmpegcore
pyffmpegcore --version
pyffmpegcore doctor
```

## Install With `pip`

If you prefer a user-level Python install:

```bash
python -m pip install --user pyffmpegcore
pyffmpegcore --version
```

## Install From A Local Checkout

If you cloned the repository and want the local CLI:

```bash
python -m pip install .
pyffmpegcore --version
```

For development:

```bash
python -m pip install -e .[dev]
pyffmpegcore doctor
```

## Verify The Install

Run:

```bash
pyffmpegcore doctor
```

You should see:

- your platform and Python version
- whether `ffmpeg` was found
- whether `ffprobe` was found

If either binary is missing, install it first and rerun `pyffmpegcore doctor`.
