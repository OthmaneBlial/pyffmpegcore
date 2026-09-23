# Release Checklist

Copy this checklist for each new version. Every box starts open; a previous release or local dry-run does not satisfy the next one. Record the exact version, source SHA, and proof URLs below, then follow [docs/RELEASING.md](docs/RELEASING.md).

- Target version and tag: candidate `0.3.0` / `v0.3.0`; not tagged or published
- Release dry-run source commit: `2d577f5ae9e83eb7343b618162a1b597adb005ce` (not a release tag)
- Latest candidate distribution artifact: [CI run 35932117971](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35932117971), built from exact source SHA `d25e6ca3b90074aab78f1588dcd7a2064daaa2d5`. Wheel `pyffmpegcore-0.3.0-py3-none-any.whl`: 94,684 bytes, SHA-256 `729b408acd6be7aa850dc7b375893cc47f7cf469978e6f8e164c679472b21310`. Sdist `pyffmpegcore-0.3.0.tar.gz`: 311,490 bytes, SHA-256 `dbd38ebfb8b8fe47492c4ca700f9d9ce3d0a6b981400e6786acdf3cc2644e7a0`. Both metadata versions match source; sdist contains README and license. Six exact-wheel OS/Python smokes and all 19 checks passed. Later `main` commits changed documentation only; package source stayed unchanged. This CI artifact is not a signed release artifact.
- CI: [35920627403](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35920627403); release bundle and six exact-wheel OS/Python checks: [35921444046](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35921444046); CodeQL: [35920627493](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35920627493); Scorecard: [35920627411](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35920627411)
- Container digest and Action integration run: not run; container build and scan are excluded by the maintainer's current instruction.
- Public PyPI and GitHub Release URLs: pending; public PyPI remains `0.2.2` and `v0.3.0` does not exist.

## Product and Documentation

- [ ] Runtime version, signed tag, wheel metadata, changelog, and release name match.
- [ ] README installation commands and badges are live and honest.
- [ ] Compatibility policy names only combinations with visible required checks.
- [ ] Security, support, contribution, and migration guidance is current.
- [ ] Notes link the exact recipes, compatibility run, before/after evidence, and user problems improved.
- [ ] External issue reporters, recipe authors, testers, and code contributors are credited by their requested name or anonymously.

## Automated Evidence

- [x] Ruff, formatting, mypy, fast tests, and the 80% full-suite coverage gate pass (CI `35920627403`, candidate source SHA above).
- [x] Python 3.10–3.14 package matrix passes (CI `35920627403`).
- [x] The same prebuilt wheel passes media smoke tests on Linux, macOS, and Windows with Python 3.10 and 3.14 (release dry-run `35921444046`).
- [x] Cold deterministic fixtures pass without cache reuse (`--force` in each release matrix job, run `35921444046`).
- [x] `twine check`, wheel contents, sdist contents, and clean isolated wheel installation pass (release dry-run `35921444046`).
- [ ] CodeQL and OpenSSF Scorecard findings are triaged. Current GitHub inventory still has 483 Trivy alerts from the image scan on `25adc431` and low-severity Scorecard alert [#15](https://github.com/OthmaneBlial/pyffmpegcore/security/code-scanning/15); no alerts were dismissed.

## Publication

- [ ] PyPI project ownership and the GitHub `pypi` environment are confirmed.
- [ ] Trusted Publishing identity is scoped to `release.yml` and the `pypi` environment.
- [x] Release workflow dry-run passes (`35921444046`, exact candidate source SHA above; publication steps skipped).
- [ ] The signed, protected version tag starts the release workflow.
- [ ] GitHub Release prerelease status matches the package development-status classifier.
- [ ] PyPI files, SHA-256 checksums, provenance attestations, and the GitHub Release describe the same artifacts.
- [ ] The automated public-endpoint wait and clean `pipx install`, `--version`, `doctor`, and `smoke-test` matrix pass after publication.
- [ ] The 60–90 second terminal cast and accessible transcript validate against the exact public version without private paths or fabricated output.

Check a box only after its evidence exists for this target version. Put final links and exact run IDs in the GitHub Release as well; leave blocked checks open with a reason.
