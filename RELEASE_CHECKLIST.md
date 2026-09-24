# Release Checklist

Copy this checklist for each new version. Every box starts open; a previous release or local dry-run does not satisfy the next one. Record the exact version, source SHA, and proof URLs below, then follow [docs/RELEASING.md](docs/RELEASING.md).

## Candidate: 0.3.2

- Source SHA: pending final candidate commit.
- Manual exact-artifact workflow: pending.
- Signed tag, provenance, PyPI files, public installs, and matching GitHub prerelease: pending; complete only through the tagged release workflow.
- No container or Docker release is included.

The verified 0.3.1 release record follows.

- Target version and tag: published `0.3.1` / `v0.3.1`, signed SSH tag at exact source SHA `562ae6ce92a8b321f15a6a250cf7802f2c9bb5bc`.
- Manual build/test run [35975145754](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35975145754) passed on the release SHA. The signed-tag release workflow [35975371541](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35975371541) passed six exact-wheel OS/Python checks, provenance, PyPI Trusted Publishing, six clean public installs, and GitHub prerelease creation.
- Published wheel `pyffmpegcore-0.3.1-py3-none-any.whl`: 101,638 bytes, SHA-256 `ea222d3dc5d09ae0ffd79c310ea415eb4edb2d7e04a87532cda939a7890d255d`. Published sdist `pyffmpegcore-0.3.1.tar.gz`: 335,713 bytes, SHA-256 `e0ff591589dd3950e11450dcecc0d1b39718c42415332568e606c98207c94074`. Both hashes match PyPI's public JSON and GitHub Release `SHA256SUMS`.
- Public links: [PyPI 0.3.1](https://pypi.org/project/pyffmpegcore/0.3.1/) and [signed GitHub prerelease](https://github.com/OthmaneBlial/pyffmpegcore/releases/tag/v0.3.1). The 63.4-second transcript and asciicast validate against the exact public wheel.
- Full CI/coverage, Python 3.11–3.13 package contracts, Scorecard, Benchmarks, and Container were not run. Docker/container work remains prohibited; GHCR/Action digest parity remains unverified.

## Product and Documentation

- [x] Runtime version, signed tag, wheel metadata, changelog, and release name match.
- [x] README installation commands are live and the recorded 0.2.2 proof is labeled as an archive.
- [x] Compatibility policy names only combinations with visible required checks.
- [ ] Security, support, contribution, and migration guidance is current.
- [ ] Notes link the exact recipes, compatibility run, before/after evidence, and user problems improved.
- [ ] External issue reporters, recipe authors, testers, and code contributors are credited by their requested name or anonymously.

## Automated Evidence

- [ ] Ruff, formatting, mypy, the full fast suite, and the 80% coverage gate pass on the latest candidate source. On release SHA `562ae6ce`, the local fast suite passed (391 passed, 102 real-media tests deselected) with Ruff, formatting, mypy, compileall, generated-doc checks, and documentation links. Hosted coverage/full CI and the full real-media suite were not run.
- [ ] Python 3.10–3.14 package matrix on the latest candidate source. The recorded hosted matrix is on older SHA `401f0622`.
- [x] The same prebuilt wheel passed media smoke tests on Linux, macOS, and Windows with Python 3.10 and 3.14 in release run [35975371541](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35975371541).
- [x] Cold deterministic fixtures passed without cache reuse (`--force`) in release run [35975371541](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35975371541).
- [x] `twine check`, wheel contents, and the sdist contract passed on the tagged release SHA; the exact wheel passed the hosted six-cell install matrix. The exact sdist also installed offline and passed `--version`, `doctor --json`, and `smoke-test --json`.
- [x] CodeQL and OpenSSF Scorecard findings are triaged in [SECURITY_TRIAGE.md](SECURITY_TRIAGE.md): no CodeQL alerts are open; low-severity Scorecard alert [#15](https://github.com/OthmaneBlial/pyffmpegcore/security/code-scanning/15) remains for external OpenSSF Best Practices enrollment. The 483 open Trivy alerts all come from the historical image scan on `25adc431`; none were dismissed. CodeQL alerts #991 and #992 are fixed by commits `8d5aa06` and `4a66b28`, not dismissed.

## Publication

- [x] PyPI project ownership and the GitHub `pypi` environment were exercised successfully by the release.
- [x] Trusted Publishing identity was accepted for `release.yml` and the `pypi` environment.
- [x] Manual `workflow_dispatch` build-and-test run [35975145754](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35975145754) passed on the exact release SHA.
- [x] The signed, protected version tag started the release workflow.
- [x] GitHub Release prerelease status matches the package development-status classifier.
- [x] PyPI files, SHA-256 checksums, provenance attestations, and the GitHub Release describe the same artifacts.
- [x] The automated public-endpoint wait and clean install, `--version`, `doctor`, and `smoke-test` checks passed on all six OS/Python anchors.
- [x] The 63.4-second terminal cast and accessible transcript validate against the exact public version without private home paths or fabricated output.

Check a box only after its evidence exists for this target version. Put final links and exact run IDs in the GitHub Release as well; leave blocked checks open with a reason.
