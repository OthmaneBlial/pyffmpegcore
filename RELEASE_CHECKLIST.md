# Release Checklist

This checklist is a gate, not a record of an older local run. The complete procedure is in [docs/RELEASING.md](docs/RELEASING.md).

## Product and Documentation

- [ ] Runtime version, signed tag, wheel metadata, changelog, and release name match.
- [ ] README installation commands and badges are live and honest.
- [ ] Compatibility policy names only combinations with visible required checks.
- [ ] Security, support, contribution, and migration guidance is current.
- [ ] Notes link the exact recipes, compatibility run, before/after evidence, and user problems improved.
- [ ] External issue reporters, recipe authors, testers, and code contributors are credited by their requested name or anonymously.

## Automated Evidence

- [ ] Ruff, formatting, mypy, fast tests, and the 80% full-suite coverage gate pass.
- [ ] Python 3.10–3.14 package matrix passes.
- [ ] The same prebuilt wheel passes media smoke tests on Linux, macOS, and Windows with Python 3.10 and 3.14.
- [ ] Cold deterministic fixtures pass without cache reuse.
- [ ] `twine check`, wheel contents, sdist contents, and clean isolated installation pass.
- [ ] CodeQL and OpenSSF Scorecard findings are triaged.

## Publication

- [ ] PyPI project ownership and the GitHub `pypi` environment are confirmed.
- [ ] Trusted Publishing identity is scoped to `release.yml` and the `pypi` environment.
- [ ] Release workflow dry-run passes.
- [ ] The signed, protected version tag starts the release workflow.
- [ ] PyPI files, SHA-256 checksums, provenance attestations, and the GitHub Release describe the same artifacts.
- [ ] Clean public `pipx install`, `--version`, `doctor`, and `smoke-test` pass after publication.

Record final links and exact check runs in the GitHub Release rather than placing a stale test count in this file.
