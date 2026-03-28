# CLI Distribution

This file defines the current public artifact strategy for the `pyffmpegcore` CLI.

## Current Strategy

The CLI is currently distributed through standard Python packaging only:

- wheel
- source distribution

The install paths built on top of that are:

- `pipx install pyffmpegcore`
- `python -m pip install --user pyffmpegcore`
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

## Release Rule

If a future release adds standalone binaries, they should not silently replace this strategy.

They need:

- an explicit build path
- explicit signing and trust notes
- startup and size validation
- CI coverage that matches the Python artifact path
