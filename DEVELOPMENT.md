# Development

This document defines the maintained local workflow for working on PyFFmpegCore.

## Current Baseline

The maintained repository baseline is:

- Python 3.10 through 3.14 for the package contract
- `ffmpeg` and `ffprobe` are required on `PATH`
- `python -m compileall pyffmpegcore tests examples` passes
- `python -m pytest` passes locally in the supported virtual environment
- the test suite includes real-media validation and generates fixtures when needed
- build artifacts, caches, and generated fixtures are ignored by git

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
python -m ruff check pyffmpegcore scripts examples tests
python -m ruff format --check pyffmpegcore scripts examples tests
python -m mypy pyffmpegcore
python -m compileall pyffmpegcore tests examples
python -m pytest -m "not real_media"
python tests/media/download_fixtures.py --force
python -m pytest --cov=pyffmpegcore --cov-report=term-missing
python -m build
python -m twine check dist/*
python -m check_wheel_contents dist/*.whl
```

Useful targeted commands:

```bash
python -m pytest tests/examples/test_examples_smoke_real.py
python -m pytest tests -m real_media
```

## Deterministic Media Fixtures

The real integration phases use local FFmpeg `lavfi` sources plus a first-party subtitle sample. The manifest records the origin, license, generator arguments, and expected media properties.

```bash
python tests/media/download_fixtures.py
```

Generated fixture files are written to `tests/media/downloads/` and are ignored by git.

The full test suite validates and regenerates them automatically when needed. Use `--force` for a true cold generation pass.

The fast tier is useful while editing. Changes to media execution, paths, filters, codecs, packaging, or platform behavior are complete only after the relevant real-media or exact-artifact tier passes. See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

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
