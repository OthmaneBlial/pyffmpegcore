# Release Checklist

Copy this checklist for each new version. Every box starts open; a previous release or local dry-run does not satisfy the next one. Record the exact version, source SHA, and proof URLs below, then follow [docs/RELEASING.md](docs/RELEASING.md).

- Target version and tag: published `0.3.0` / `v0.3.0`, signed SSH tag at exact source SHA `492d4b0a808cd429b75b2d21735652260eee9296`.
- Manual build/test run [35971029965](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35971029965) and CodeQL [35971015146](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35971015146) passed on the release SHA. The signed-tag release workflow [35971504440](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35971504440) completed all jobs, including six exact-wheel OS/Python media checks, provenance attestations, PyPI Trusted Publishing, six clean public installs, and matching GitHub prerelease creation.
- Published wheel `pyffmpegcore-0.3.0-py3-none-any.whl`: 101,305 bytes, SHA-256 `8ed1b315b3326cc115e5df4bd1ac32d69b6c77175663d6c630cf3e75c3186df7`. Published sdist `pyffmpegcore-0.3.0.tar.gz`: 334,320 bytes, SHA-256 `e01753d0315525ebd99c7da2c2dc7a09cf6d13af488fc81fe9692a8a2f925e78`. Both hashes match PyPI's public JSON and the GitHub Release `SHA256SUMS`; the artifact report records the 272-file sdist contract.
- Public links: [PyPI 0.3.0](https://pypi.org/project/pyffmpegcore/0.3.0/) and [signed GitHub prerelease](https://github.com/OthmaneBlial/pyffmpegcore/releases/tag/v0.3.0). The 63.5-second transcript and asciicast validate against the exact public wheel.
- Full CI/coverage, the Python 3.11–3.13 package contracts on the release SHA, Scorecard, Benchmarks, and Container were not run. The maintainer prohibits Docker/container work; GHCR/Action digest parity remains unverified.

## Product and Documentation

- [x] Runtime version, signed tag, wheel metadata, changelog, and release name match.
- [x] README installation commands are live and the recorded 0.2.2 proof is labeled as an archive.
- [ ] Compatibility policy names only combinations with visible required checks.
- [ ] Security, support, contribution, and migration guidance is current.
- [ ] Notes link the exact recipes, compatibility run, before/after evidence, and user problems improved.
- [ ] External issue reporters, recipe authors, testers, and code contributors are credited by their requested name or anonymously.

## Automated Evidence

- [ ] Ruff, formatting, mypy, the full fast suite, and the 80% coverage gate pass on the latest candidate source. Local CI fast suite on code SHA `1ec6714` passed (374 passed, 102 real-media deselected), with Ruff, formatting, mypy, compileall, and docs checks. CodeQL and Scorecard also passed on that SHA. Hosted coverage/full CI is older (`401f0622`); full real-media suite remains unrun.
- [ ] Python 3.10–3.14 package matrix on the latest candidate source. The recorded hosted matrix is on older SHA `401f0622`.
- [x] The same prebuilt wheel passed media smoke tests on Linux, macOS, and Windows with Python 3.10 and 3.14 in release run [35971504440](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35971504440).
- [x] Cold deterministic fixtures passed without cache reuse (`--force`) in release run [35971504440](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35971504440).
- [x] `twine check`, wheel contents, and the 272-file sdist contract passed on the tagged release SHA; the exact wheel passed the hosted six-cell install matrix. The exact sdist also installed offline and passed `--version`, `doctor --json`, and `smoke-test --json`.
- [x] CodeQL and OpenSSF Scorecard findings are triaged in [SECURITY_TRIAGE.md](SECURITY_TRIAGE.md): no CodeQL alerts are open; low-severity Scorecard alert [#15](https://github.com/OthmaneBlial/pyffmpegcore/security/code-scanning/15) remains for external OpenSSF Best Practices enrollment. The 483 open Trivy alerts all come from the historical image scan on `25adc431`; none were dismissed. CodeQL alerts #991 and #992 are fixed by commits `8d5aa06` and `4a66b28`, not dismissed.

## Publication

- [x] PyPI project ownership and the GitHub `pypi` environment were exercised successfully by the release.
- [x] Trusted Publishing identity was accepted for `release.yml` and the `pypi` environment.
- [x] Manual `workflow_dispatch` build-and-test run [35971029965](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35971029965) passed on the exact release SHA.
- [x] The signed, protected version tag started the release workflow.
- [x] GitHub Release prerelease status matches the package development-status classifier.
- [x] PyPI files, SHA-256 checksums, provenance attestations, and the GitHub Release describe the same artifacts.
- [x] The automated public-endpoint wait and clean install, `--version`, `doctor`, and `smoke-test` checks passed on all six OS/Python anchors.
- [x] The 63.5-second terminal cast and accessible transcript validate against the exact public version without private home paths or fabricated output.

Check a box only after its evidence exists for this target version. Put final links and exact run IDs in the GitHub Release as well; leave blocked checks open with a reason.
