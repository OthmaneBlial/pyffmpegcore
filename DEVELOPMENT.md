# Development

This document defines the maintained local workflow for working on PyFFmpegCore.

## Current Baseline

As of March 28, 2026, the repository baseline is:

- `ffmpeg` and `ffprobe` are required on `PATH`
- `python -m compileall pyffmpegcore tests examples` passes
- `python -m pytest` passes locally in the supported virtual environment
- the test suite includes real-media validation and auto-downloads fixtures when needed
- build artifacts, caches, and downloaded fixtures are ignored by git

## Supported Local Workflow

Use a local virtual environment instead of relying on global Python packages.

```bash
python -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
```

The `dev` extra is the supported way to install local test and build tooling for this repository.

## Validation Commands

Run these commands before and after meaningful changes:

```bash
python -m compileall pyffmpegcore tests examples
python -m pytest
python -m build
```

Useful targeted commands:

```bash
python -m pytest tests/examples/test_examples_smoke_real.py
python -m pytest tests -m real_media
```

## Internet Media Fixtures

The real integration phases use internet-backed sample files pinned by checksum metadata.

```bash
python tests/media/download_fixtures.py
```

Downloaded fixture files are written to `tests/media/downloads/` and are ignored by git.

The full test suite will also download them automatically on first use.

## FFmpeg Checks

Confirm the media tools are available before running feature or integration tests:

```bash
ffmpeg -version
ffprobe -version
```

## Notes

- Example scripts are treated as part of the public contract and now have dedicated smoke coverage.
- `FFprobeRunner.probe()` intentionally returns simplified metadata rather than the raw FFprobe JSON payload.
- Real-media validation matters more than mocked command assertions for this project.
