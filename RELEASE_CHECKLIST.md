# Release Checklist

Copy this checklist for each new version. Every box starts open; a previous release or local dry-run does not satisfy the next one. Record the exact version, source SHA, and proof URLs below, then follow [docs/RELEASING.md](docs/RELEASING.md).

- Target version and tag: candidate `0.3.0` / `v0.3.0`; not tagged or published
- Last manual build/test-only dispatch source commit: `2d577f5ae9e83eb7343b618162a1b597adb005ce` (not a release tag)
- Latest candidate distribution artifact: [CI run 35940356100](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35940356100), built from exact source SHA `291c08973cd4fe74948af189ea82df99c9890c4e`. Wheel `pyffmpegcore-0.3.0-py3-none-any.whl`: 94,687 bytes, SHA-256 `2084030dbfdcfe93d316bb19d006576e270c1ed4328a37e7e68f7d6f6b70d5b8`. Sdist `pyffmpegcore-0.3.0.tar.gz`: 308,186 bytes, SHA-256 `634646a2914ce94f89e4327af66379cce28d68d00800585da39d71f6ca1ada24`. `twine check`, wheel contents, sdist contents, and all six exact-wheel OS/Python smokes passed. CI, CodeQL [35940356128](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35940356128), and Scorecard [35940356115](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35940356115) passed. Rebuilding from a clean `git archive` at the exact SHA with `SOURCE_DATE_EPOCH=1790211123` reproduced both files byte-for-byte. The exact wheel passed local pip install, `--version`, `doctor --json`, and `smoke-test --json`; the exact sdist installed offline and passed `--version` and `smoke-test`. The artifact remains untagged, unsigned, and unpublished.
- Current full CI and exact-wheel matrix: [35940356100](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35940356100); last manual build/test-only dispatch: [35921444046](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35921444046); CodeQL: [35940356128](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35940356128); Scorecard: [35940356115](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35940356115)
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

- [x] Ruff, formatting, mypy, fast tests, and the 80% full-suite coverage gate pass (CI `35940356100`, candidate source SHA above).
- [x] Python 3.10–3.14 package matrix passes (CI `35940356100`).
- [x] The same prebuilt wheel passes media smoke tests on Linux, macOS, and Windows with Python 3.10 and 3.14 (CI `35940356100`).
- [x] Cold deterministic fixtures pass without cache reuse (`--force` in each release matrix job, run `35921444046`).
- [x] `twine check`, wheel contents, sdist contents, and clean isolated wheel installation pass (CI `35940356100` and exact local artifact check above).
- [ ] CodeQL and OpenSSF Scorecard findings are triaged. Current GitHub inventory still has 483 Trivy alerts from the image scan on `25adc431` and low-severity Scorecard alert [#15](https://github.com/OthmaneBlial/pyffmpegcore/security/code-scanning/15); no alerts were dismissed.

## Publication

- [ ] PyPI project ownership and the GitHub `pypi` environment are confirmed.
- [ ] Trusted Publishing identity is scoped to `release.yml` and the `pypi` environment.
- [x] Manual `workflow_dispatch` build-and-test run passes (`35921444046`, exact candidate source SHA above; publication steps skipped by event type).
- [ ] The signed, protected version tag starts the release workflow.
- [ ] GitHub Release prerelease status matches the package development-status classifier.
- [ ] PyPI files, SHA-256 checksums, provenance attestations, and the GitHub Release describe the same artifacts.
- [ ] The automated public-endpoint wait and clean `pipx install`, `--version`, `doctor`, and `smoke-test` matrix pass after publication.
- [ ] The 60–90 second terminal cast and accessible transcript validate against the exact public version without private paths or fabricated output.

Check a box only after its evidence exists for this target version. Put final links and exact run IDs in the GitHub Release as well; leave blocked checks open with a reason.
