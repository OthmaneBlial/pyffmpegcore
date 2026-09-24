# Release Checklist

Copy this checklist for each new version. Every box starts open; a previous release or local dry-run does not satisfy the next one. Record the exact version, source SHA, and proof URLs below, then follow [docs/RELEASING.md](docs/RELEASING.md).

- Target version and tag: candidate `0.3.0` / `v0.3.0`; not tagged or published
- Latest locally rebuilt candidate: two builds from the clean archive at exact source SHA `ba981e9d3c7d451baabd3e2662b94e5a303fc979` with `SOURCE_DATE_EPOCH=1790225853` produced identical wheel (`98,262` bytes; SHA-256 `45633903733ac04cccb96d33eca65e9d33cbd3c249cf39d723d160b79d984e22`) and sdist (`323,909` bytes; SHA-256 `75041d8efafc264bce97b0f8a74e498c621e3891b7167e28d483b108f6c11ddc`). `twine check`, `check-wheel-contents`, and the sdist content contract passed. The exact wheel installed offline in a clean venv; the exact sdist installed offline into an isolated target using the local build backend. Both passed `--version`, `doctor --json`, and `smoke-test --json` on macOS arm64, Python 3.14.6, FFmpeg 9.0.1. This is local evidence only. Two later docs-only commits changed files included in the sdist; rebuild from the final release SHA. No hosted OS matrix, attestation, tag, or publication exists for this build.
- Latest hosted release artifact: [Release run 35941884095](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35941884095), built from exact source SHA `401f0622a69b88d0beebfc32203d649070af0d86`. Wheel `pyffmpegcore-0.3.0-py3-none-any.whl`: 94,687 bytes, SHA-256 `c6defa062bffb9aea449d735049a05890e9f70254a5b427457743e509aecdd06`. Sdist `pyffmpegcore-0.3.0.tar.gz`: 308,766 bytes, SHA-256 `fffc1fe4e88e62b320d833a573fe3437f5237a7f680a2eeb62758ba30a292974`. `twine check`, wheel contents, and all six exact-wheel OS/Python smokes passed. Rebuilding from a clean `git archive` at the exact SHA with `SOURCE_DATE_EPOCH=1790211959` reproduced both files byte-for-byte. The exact wheel passed local pip install, `--version`, `doctor --json`, and `smoke-test --json`; the exact sdist installed offline and passed `--version` and `smoke-test`. Full CI [35941424672](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35941424672), CodeQL [35941424727](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35941424727), and Scorecard [35941424803](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35941424803) passed on the same SHA. Manual `workflow_dispatch` built and tested this bundle; attestations, PyPI, public-install, and GitHub Release jobs were skipped. The artifact remains untagged, unsigned, and unpublished.
- Latest hosted full CI and release-artifact checks are on prior source SHA `401f0622a69b88d0beebfc32203d649070af0d86`: CI [35941424672](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35941424672), manual build/test [35941884095](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35941884095), CodeQL [35941424727](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35941424727), and Scorecard [35941424803](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35941424803). On candidate code SHA `ba981e9d3c7d451baabd3e2662b94e5a303fc979`, CodeQL [35957849103](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35957849103) and Scorecard [35957849130](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35957849130) passed; full CI, Benchmarks, Container, and the hosted release matrix did not run.
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

- [ ] Ruff, formatting, mypy, the full fast suite, and the 80% coverage gate pass on the latest candidate source. Ruff, formatting, mypy, and 60 focused tests pass locally on SHA `ba981e9`; the full suite/coverage CI run is older (`401f0622`).
- [ ] Python 3.10–3.14 package matrix on the latest candidate source. The recorded hosted matrix is on older SHA `401f0622`.
- [ ] The same prebuilt wheel passes media smoke tests on Linux, macOS, and Windows with Python 3.10 and 3.14 for the latest candidate source. The recorded release matrix is on older SHA `401f0622`.
- [ ] Cold deterministic fixtures pass without cache reuse (`--force`) on the latest candidate source. The recorded release run is on older SHA `401f0622`.
- [x] `twine check`, wheel contents, sdist contents, and clean isolated wheel installation pass (release run `35941884095` and exact local artifact check above).
- [x] CodeQL and OpenSSF Scorecard findings are triaged in [SECURITY_TRIAGE.md](SECURITY_TRIAGE.md): no CodeQL alerts are open; low-severity Scorecard alert [#15](https://github.com/OthmaneBlial/pyffmpegcore/security/code-scanning/15) remains for external OpenSSF Best Practices enrollment. The 483 open Trivy alerts all come from the historical image scan on `25adc431`; none were dismissed.

## Publication

- [ ] PyPI project ownership and the GitHub `pypi` environment are confirmed.
- [ ] Trusted Publishing identity is scoped to `release.yml` and the `pypi` environment.
- [ ] Manual `workflow_dispatch` build-and-test run on the latest candidate source. Run `35941884095` passed on older SHA `401f0622`; publication steps were skipped by event type.
- [ ] The signed, protected version tag starts the release workflow.
- [ ] GitHub Release prerelease status matches the package development-status classifier.
- [ ] PyPI files, SHA-256 checksums, provenance attestations, and the GitHub Release describe the same artifacts.
- [ ] The automated public-endpoint wait and clean `pipx install`, `--version`, `doctor`, and `smoke-test` matrix pass after publication.
- [ ] The 60–90 second terminal cast and accessible transcript validate against the exact public version without private paths or fabricated output.

Check a box only after its evidence exists for this target version. Put final links and exact run IDs in the GitHub Release as well; leave blocked checks open with a reason.
