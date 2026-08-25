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

## Contribution Ladder

Start at the lowest level that matches the change. Each level is useful on its
own and should not require unrelated refactoring.

1. **Docs and recipes** — improve a task contract, troubleshooting step, or
   accessible example under `docs/`; run the documentation checks.
2. **Fixtures and tests** — add deterministic media coverage or a contract test
   under `tests/`; never commit generated media.
3. **Platform support** — reproduce a Linux, macOS, Windows, shell, Python, or
   FFmpeg-build difference and update the compatibility evidence.
4. **Workflow and core changes** — change typed plans, preflight, execution, or
   receipts only with an agreed issue, failure tests, real-media proof, and
   migration analysis.

Issues labeled `good first issue` include exact file pointers, acceptance
criteria, and verification commands. `help wanted` means the maintainer has
committed to reviewing a focused solution; it is not an unowned wishlist.

## Test Tiers

Fast checks do not intentionally execute the full real-media matrix:

```bash
python -m ruff check pyffmpegcore scripts examples tests
python -m ruff format --check pyffmpegcore scripts examples tests
python -m mypy pyffmpegcore scripts
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

## Review and Credit

During active maintenance, the target is an initial issue response within seven
calendar days and a first focused pull-request review within fourteen. These are
best-effort targets, not paid support guarantees; a maintenance pause will be
stated in `SUPPORT.md` and the repository header rather than leaving contributors
guessing.

Release notes credit external code contributors automatically and must also name
issue reporters, recipe authors, and independent testers whose work materially
changed the release. Tell us the name or handle you want credited, or request
anonymous credit.
