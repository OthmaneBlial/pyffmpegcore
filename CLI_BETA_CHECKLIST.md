# CLI Beta Acceptance

The beta is accepted from immutable CI and release evidence, not a copied local test count or temporary-directory transcript.

## Required Evidence

- [CI](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/ci.yml) is green for quality, Python 3.10–3.14, 80% full-suite coverage, distribution build, and exact-wheel smoke tests.
- The exact wheel passes on Linux, macOS, and Windows with Python 3.10 and 3.14.
- [Cold-fixture compatibility](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/fixtures.yml) regenerates every fixture without cache reuse.
- `twine check`, wheel-content checks, SHA-256 generation, isolated install, `doctor`, and `smoke-test` pass.
- Runtime version, signed tag, wheel/sdist metadata, PyPI project, and GitHub Release agree.
- CodeQL and OpenSSF Scorecard findings are triaged.

## User Contract

- Invalid syntax exits `2`; missing tools exit `3`; invalid inputs or refused overwrites exit `4`; processing failures exit `5`; partial batches exit `6`.
- Global flags work before and after subcommands.
- Incomplete nested commands cannot return success.
- Runtime subprocesses use argument arrays and do not invoke a shell.
- Public examples use deterministic or user-owned media.

## Final Public Verification

After publication, a clean machine must pass:

```bash
pipx install pyffmpegcore
pyffmpegcore --version
pyffmpegcore doctor
pyffmpegcore smoke-test
```

Place the exact run links, checksums, compatibility statement, and known limitations in the GitHub Release. Do not mark this beta public while the PyPI endpoint or any command above fails.
