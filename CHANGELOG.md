# Changelog

All notable changes are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Deterministic, locally generated audio, video, image, and subtitle fixtures.
- Package-installed `smoke-test` proof workflow.
- Python 3.10–3.14 package matrix and exact-artifact smoke checks on Linux, macOS, and Windows.
- Lint, formatting, static typing, 80% coverage, package-content, provenance, CodeQL, and Scorecard gates.
- Security, support, contribution, compatibility, and release documentation.
- Versioned `ExecutionPlan`, `PreflightReport`, `ProgressEvent`, and `JobResult` contracts.
- `--dry-run`, `--explain`, `--plan-json`, and executing `--result-json` modes for every writing command.
- Explicit CLI timeout and temporary-file retention policies with child-process-safe keyboard cancellation.
- Separated CLI registration and validation layers while preserving the public command contract.

### Changed

- Global CLI options now behave consistently before or after subcommands.
- Nested command groups now reject incomplete invocations with exit code `2`.
- The package version is sourced from `pyffmpegcore.__version__`.
- All CLI writing commands now compile, preflight, and execute through the shared typed workflow engine.
- Repository examples now consume the same public `WorkflowEngine` and curated plans as the CLI; unsupported experimental raw-command variants were removed.
- `FFmpegRunner` convenience methods now use typed plans and return `JobResult`; only the guarded low-level `run(args)` escape hatch returns `CompletedProcess`.

### Fixed

- Subtitle and waveform commands work with current FFmpeg filter syntax where the required capabilities are available.
- Fixture validation no longer depends on mutable third-party downloads.

[Unreleased]: https://github.com/OthmaneBlial/pyffmpegcore/commits/main
