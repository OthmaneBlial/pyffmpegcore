# CLI Distribution

This file defines the current public artifact strategy for the `pyffmpegcore` CLI.

## Current Strategy

The CLI's downloadable Python release artifacts are:

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

- `pipx install "pyffmpegcore==0.2.2"`
- `python -m pip install --user "pyffmpegcore==0.2.2"`
- `./install.sh`
- `.\install.ps1`

The project also publishes a [digest-pinned container image](docs/container.md)
and a [GitHub Action](docs/github-action.md) for CI workflows. Those are
separate integration channels, not standalone desktop executables or assets
inside the wheel/sdist. Their source revision and digest must be checked
against the specific run cited by each guide before a release announces them.

## What We Are Not Shipping Yet

We are not shipping standalone binaries in this release.

Why:

- they increase maintenance cost
- they change trust and signing expectations
- they create larger artifacts to validate
- the Python packaging path is already working and tested

That means the honest release story right now is:

- wheel and sdist remain the downloadable Python release artifacts
- container and Action users get separately versioned, pinned integration paths
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
