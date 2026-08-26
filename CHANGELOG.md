# Changelog

All notable changes are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.1] - 2026-08-26

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
- Deterministic rich-media fixtures now cover stream selection, chapters, cover art, rotation, VFR, and Unicode metadata.
- Failed jobs remove newly created incomplete outputs, and the sdist enforces a self-contained testable-source contract.
- Privacy-redacted run receipts with opt-in hashes, offline validation, canonical migration, and doctor-backed bug reports.
- Explicit UTF-8 subprocess decoding for Unicode FFprobe facts on Windows.
- Versioned workflow capability-catalog reports across Linux, macOS, and Windows compatibility jobs.
- Structured FFmpeg progress with an explicit unsupported-option-only legacy stderr fallback.
- Measured target-size before/after proof in human, machine-result, and receipt output.
- Executable built-in profiles with output-contract validation and cross-platform golden media smoke tests.
- Bounded mixed-media batches with strict manifests, JSONL events, per-item receipts, classified retries, and signature-based resume.
- Typed JSON/TOML pipelines with DAG preflight, graph output, cancellation/resume, optional content-aware caching, secret masking, schema migration, and three golden templates.
- A pinned non-root multi-architecture container supply chain with pre-publish smoke tests, blocking vulnerability scan, SBOM, provenance, and digest attestation.
- A digest-pinned composite GitHub Action that runs typed pipelines and preserves receipts, events, resume state, results, and selected outputs.
- A versioned overhead benchmark for startup, exact-plan processing, package size, and pipeline-cache behavior, plus documented pipx and uv tool installs.
- Dated, privacy-redacted before/after evidence for the web-video, exact-size, and podcast flagship recipes.
- Technical notes on capability preflight, exact-size budgeting, deterministic plans, and privacy-safe receipts.
- `convert --preserve-all-streams` for explicit lossless remuxing of every
  video, audio, subtitle, attachment, and data stream, with conflicting
  re-encoding options rejected before execution.
- Source-backed recipe and troubleshooting paths for recurring web-video,
  target-size, stream-selection, and subprocess-stall questions.

### Changed

- Global CLI options now behave consistently before or after subcommands.
- Nested command groups now reject incomplete invocations with exit code `2`.
- The package version is sourced from `pyffmpegcore.__version__`.
- All CLI writing commands now compile, preflight, and execute through the shared typed workflow engine.
- Repository examples now consume the same public `WorkflowEngine` and curated plans as the CLI; unsupported experimental raw-command variants were removed.
- `FFmpegRunner` convenience methods now use typed plans and return `JobResult`; only the guarded low-level `run(args)` escape hatch returns `CompletedProcess`.

### Fixed

- Release verification now restores the annotated tag object after checkout
  and proves that the verified tag resolves to the exact workflow commit.
- Subtitle and waveform commands work with current FFmpeg filter syntax where the required capabilities are available.
- Fixture validation no longer depends on mutable third-party downloads.
- Managed FFmpeg jobs disable interactive standard input so background jobs do
  not poll the console.
- FFmpeg output decodes explicitly as UTF-8 with replacement, preventing
  non-Latin metadata from killing Windows pipe-drain threads and stalling the
  media process.

[Unreleased]: https://github.com/OthmaneBlial/pyffmpegcore/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/OthmaneBlial/pyffmpegcore/releases/tag/v0.2.1
