# Contributing to PyFFmpegCore

Thank you for helping make repeatable FFmpeg work safer and easier to explain.

## Start With the Right Route

- Use the bug form for reproducible defects.
- Use the recipe request form for a real media workflow that should become a documented, tested recipe.
- Use a discussion or the support routes in [SUPPORT.md](SUPPORT.md) for questions.
- Report security problems privately through [SECURITY.md](SECURITY.md).

For a substantial behavior or command-surface change, open an issue first so the contract can be agreed before implementation.

## Local Setup

Follow [DEVELOPMENT.md](DEVELOPMENT.md). The short version is:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Windows PowerShell activates the environment with `.venv\Scripts\Activate.ps1`.

## Test Tiers

Fast checks do not intentionally execute the full real-media matrix:

```bash
python -m ruff check pyffmpegcore scripts examples tests
python -m ruff format --check pyffmpegcore scripts examples tests
python -m mypy pyffmpegcore
python -m pytest -m "not real_media"
```

The release-relevant tier generates deterministic local media and runs the complete suite:

```bash
python tests/media/download_fixtures.py --force
python -m pytest --cov=pyffmpegcore --cov-report=term-missing
```

Changes to command construction, codecs, filters, paths, progress, packaging, or platform behavior need real FFmpeg evidence. Mock-only tests are not sufficient for those changes.

## Pull Requests

Keep each PR focused. Update tests and user-facing documentation with behavior changes. Do not commit generated media, build artifacts, caches, credentials, or personal media. Complete the pull-request template and state exactly what was and was not verified.

By participating, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
