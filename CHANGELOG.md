# Changelog

All notable changes are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Deterministic, locally generated audio, video, image, and subtitle fixtures.
- Package-installed `smoke-test` proof workflow.
- Python 3.10–3.14 package matrix and exact-artifact smoke checks on Linux, macOS, and Windows.
- Lint, formatting, static typing, 80% coverage, package-content, provenance, CodeQL, and Scorecard gates.
- Security, support, contribution, compatibility, and release documentation.

### Changed

- Global CLI options now behave consistently before or after subcommands.
- Nested command groups now reject incomplete invocations with exit code `2`.
- The package version is sourced from `pyffmpegcore.__version__`.

### Fixed

- Subtitle and waveform commands work with current FFmpeg filter syntax where the required capabilities are available.
- Fixture validation no longer depends on mutable third-party downloads.

[Unreleased]: https://github.com/OthmaneBlial/pyffmpegcore/commits/main
