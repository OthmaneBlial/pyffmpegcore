# CLI Distribution

This file defines the current public artifact strategy for the `pyffmpegcore` CLI.

## Current Strategy

The CLI is currently distributed through standard Python packaging only:

- wheel
- source distribution

The source distribution is deliberately a **self-contained testable source
artifact**, not a minimal runtime-only archive. It includes the package,
documentation, examples, build/validation scripts, tests, and deterministic
fixture manifest/generator. It excludes generated media, caches, coverage,
the built documentation site, repository research notes, and VCS data. The
artifact builder rejects any unreviewed top-level addition or missing required
path, so this boundary cannot drift silently.

The install paths built on top of that are:

- `pipx install git+https://github.com/OthmaneBlial/pyffmpegcore.git@main` until PyPI publication
- `python -m pip install --user git+https://github.com/OthmaneBlial/pyffmpegcore.git@main` until PyPI publication
- `./install.sh`
- `.\install.ps1`

## What We Are Not Shipping Yet

We are not shipping standalone binaries in this release.

Why:

- they increase maintenance cost
- they change trust and signing expectations
- they create larger artifacts to validate
- the Python packaging path is already working and tested

That means the honest release story right now is:

- Python package artifacts are first-class
- installer scripts are bootstrap helpers around those package artifacts
- standalone executables can be reconsidered later if there is real demand

## Build The Supported Artifacts

From the repository root:

```bash
python scripts/build_cli_artifacts.py
```

For JSON output:

```bash
python scripts/build_cli_artifacts.py --json
```

This builds:

- `pyffmpegcore-<version>.tar.gz`
- `pyffmpegcore-<version>-py3-none-any.whl`

And reports:

- filename
- artifact type
- size in bytes
- SHA256 digest
- the versioned source-distribution content-contract result

## Release Rule

If a future release adds standalone binaries, they should not silently replace this strategy.

They need:

- an explicit build path
- explicit signing and trust notes
- startup and size validation
- CI coverage that matches the Python artifact path
