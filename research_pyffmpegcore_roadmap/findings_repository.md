# Repository product and technical audit

Audit date: 2026-08-25. Repository HEAD: `0e17999` on `main`.

## Executive verdict

PyFFmpegCore is a credible **pre-release CLI**, not yet a consumable public product. Its unusually broad FFmpeg workflow coverage and real-media tests are strong foundations. The immediate adoption blockers are more basic: the documented install target does not exist on PyPI, there is no tag or GitHub release, and the advertised practice-fixture flow no longer reproduces. A user following the README cannot currently reach a trustworthy first success.

The project should not add many more media commands yet. It should first turn the existing surface into a published, reproducible, well-defined product.

## What is already strong

- **Substantial CLI surface:** `pyffmpegcore/cli.py` exposes 14 top-level commands/groups and 12 nested actions across diagnostics, conversion, compression, extraction, thumbnails, waveforms, speed, concat, subtitles, audio, and images. It also has stable exit-code constants, overwrite protection, quiet mode, progress output, JSON for `doctor`/`probe`, and shell completion.
- **Useful Python core:** `pyffmpegcore/runner.py`, `probe.py`, and `progress.py` provide dependency-free synchronous wrappers for common operations, simplified probing, and progress callbacks. Arbitrary FFmpeg arguments remain possible through `FFmpegRunner.run()`.
- **Good practical documentation:** `README.md` has a five-minute path and copy-paste tasks; `EXAMPLES.md` contains 22 CLI recipes; `CLI_INSTALL.md`, `CLI_HELP.md`, `CLI_PLATFORM_NOTES.md`, `DEVELOPMENT.md`, and the two checklists make intent explicit.
- **Real examples, not toy snippets:** 11 scripts under `examples/` cover conversion, metadata, compression, thumbnails, waveforms, speed, concat, subtitles, audio workflows, and image batches. Tests treat these examples as contracts.
- **Serious test investment:** 171 tests are currently collected. In a clean temporary environment with the package installed, `pytest -m "not real_media"` produced **93 passed, 1 skipped, 77 deselected** on Python 3.14.6/macOS arm64. Test code covers argument construction, CLI behavior, installation, artifacts, special-character paths, examples, and real media.
- **Buildable package:** `scripts/build_cli_artifacts.py` successfully produced a 28,052-byte wheel and a 64,417-byte sdist for 0.1.2 in this audit. `pyproject.toml` correctly defines the `pyffmpegcore` console entry point, and the wheel contains it.
- **Meaningful CI:** `.github/workflows/ci.yml` includes fast tests/build, clean-install CLI smoke on Linux/macOS/Windows, real-media smoke, and a full real-media push gate. The last public run was green across all six jobs: [GitHub Actions run 23687576632](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/23687576632).

## P0 blockers: make the current product real

### 1. The advertised installation path is nonexistent

- `README.md`, `CLI_INSTALL.md`, `install.sh`, and `install.ps1` all default to `pipx install pyffmpegcore` or `pip install pyffmpegcore`.
- The official [PyPI project URL](https://pypi.org/project/pyffmpegcore/) and JSON endpoint return 404 as of the audit.
- The public repository has **no tags and no GitHub releases**: [releases](https://github.com/OthmaneBlial/pyffmpegcore/releases), [tags](https://github.com/OthmaneBlial/pyffmpegcore/tags).
- There is no release/publish workflow under `.github/workflows/`; CI only builds ephemeral artifacts. `RELEASE_CHECKLIST.md` proves an old build, not publication.
- Consequently the three PyPI badges at the top of `README.md` and the default one-command installers do not represent a working product.

**Roadmap implication:** ship a real 0.1.x release before marketing. Add tagged versioning, PyPI Trusted Publishing, a GitHub release with wheel/sdist/checksums and release notes, `twine check`, install-from-PyPI smoke tests, and a rollback/yank procedure. Do not label artifact-building as release completion.

### 2. The promised reproducible demo/test path is broken today

- `README.md`, `EXAMPLES.md`, and `DEVELOPMENT.md` tell users to run `python tests/media/download_fixtures.py`.
- A fresh run verified five assets, then failed on `sample_image_png.png`: manifest SHA-256 `92277a...` versus downloaded SHA-256 `8bf88c...`. Evidence is in the mutable third-party URL recorded in `tests/media/manifest.json`.
- The full real-media and clean-install flows therefore cannot currently bootstrap from scratch, despite March's green CI/checklists. The CI cache can also hide upstream fixture drift until a cache miss.
- Documentation says 105 tests (`README.md`, `RELEASE_CHECKLIST.md`), while the repository now collects 171, another sign that verification claims are snapshots rather than maintained evidence.

**Roadmap implication:** replace mutable third-party fixtures with tiny, redistribution-safe pinned assets or deterministic FFmpeg-generated fixtures. Add a scheduled cold-cache fixture job. Put current test/compatibility evidence in generated CI badges or a maintained matrix instead of dated prose.

### 3. The zero-to-success experience depends on a repository checkout

- A `pipx` user cannot access `tests/media/download_fixtures.py`, yet the README's practice path assumes the source tree.
- The package does not offer `demo`, `init`, or a locally generated sample, and `doctor` verifies only binary presence/version, not the encoders and filters required by defaults such as `libx264`, `libmp3lame`, `libopus`, `subtitles`, `showwavespic`, and `loudnorm` (`pyffmpegcore/cli.py`, `runner.py`). A green doctor can precede a failed first command.

**Roadmap implication:** provide a package-installed smoke/demo command that generates a tiny synthetic input locally, performs one useful operation, probes the output, and cleans up. Upgrade `doctor` to report the exact capability matrix needed by shipped workflows, with actionable OS-specific remedies.

## P1 product and engineering gaps

### CLI correctness and automation contract

- Global options are defined on both the root parser and subparsers (`add_global_arguments()` / `build_parser()` in `pyffmpegcore/cli.py`). Values placed in the conventional root position are silently reset by subparser defaults: `pyffmpegcore --verbose doctor` parses as `verbose=False`, and `pyffmpegcore --force convert ...` parses as `force=False`; placing them after the command works. Tests cover only the latter shape.
- `--verbose` is advertised but `ctx.verbose` is never read anywhere in `pyffmpegcore/cli.py`; it has no behavior.
- Invoking an incomplete group such as `pyffmpegcore subtitles` or `pyffmpegcore speed` prints the root help and exits **0**, so scripts cannot distinguish incomplete usage from success.
- Machine-readable output exists only for `doctor` and `probe`. Conversion commands have no JSON result, dry-run, normalized command preview, timing, input/output metadata receipt, or stable per-file report for automation.

**Roadmap implication:** lock a CLI contract with golden tests for option placement, nested usage errors, exit codes, stdout/stderr, and JSON schemas. Make verbose useful, add `--dry-run`/`--json` job receipts, and keep human output separate from machine output.

### Split identity and duplicated feature ownership

- `README.md` positions a “terminal-first media toolkit,” while `pyproject.toml` and the live GitHub description still call it “a lightweight Python wrapper.” The name also suggests a library, but docs explicitly make the Python API secondary.
- The CLI is 2,257 lines while `runner.py` is 568 lines. Several CLI-only workflows build FFmpeg commands directly; examples reimplement speed, concat, subtitle, audio, and image logic; codec maps and filter helpers are duplicated across `cli.py`, `runner.py`, and examples. This creates three surfaces that can drift.
- The CLI has far more functionality than the documented public Python API. `README.md` shows only one `extract_audio()` snippet and no API reference, error model, parameter reference, output contract, or stability policy.

**Roadmap implication:** choose and state one product promise. A defensible direction is a task-oriented CLI powered by one reusable typed workflow layer. Move command construction and validation out of handlers/examples, make both CLI and Python call the same operations, and document which API is stable.

### Weak library contracts despite a broad feature set

- Most Python workflow options arrive through untyped `**kwargs`; typos may be ignored and editor discovery is poor (`pyffmpegcore/runner.py`). Results are raw `subprocess.CompletedProcess` values rather than a stable domain result.
- Failures are inconsistent: missing binaries and probe failures raise `RuntimeError`; FFmpeg processing failures return nonzero results; validation raises `ValueError`. Callers must know each path.
- Library helpers append `-y` and overwrite outputs by default, unlike the safer CLI `--force` policy.
- `FFprobeRunner.probe()` exposes only a simplified dictionary and drops useful raw stream/tag/disposition/color/rotation data; there is no raw mode or typed metadata model.
- There is no cancellation, timeout, async job API, structured logging, or resource-control contract. These matter more for dependable integration than another preset command.

**Roadmap implication:** introduce typed option/result/error models, explicit overwrite and timeout policies, raw-plus-simplified probe modes, command inspection, and cancellation. Preserve the low-level escape hatch while making common paths difficult to misuse.

### Compatibility and quality claims are broader than their evidence

- `pyproject.toml` claims Python 3.8+ and classifiers through 3.12, but every CI job uses only Python 3.12. FFmpeg versions/build capabilities are not captured as a tested matrix.
- Coverage configuration exists, but `pytest-cov` is not a dev dependency and CI has no coverage threshold/report. There is no formatter/linter, type checker, pre-commit, dependency/security audit, or packaging metadata validation gate.
- `__version__` in `pyffmpegcore/__init__.py` duplicates the version in `pyproject.toml`, making release drift possible.
- The generated sdist includes top-level test files but omits their support modules and subtrees (`tests/media`, `tests/examples`, `tests/media_utils.py`, `tests/cli_helpers.py`, `tests/mp4_utils.py`) and omits the CLI documentation files. It is therefore neither a clean runtime source artifact nor a self-contained test source artifact.

**Roadmap implication:** test the claimed Python range, add a small supported FFmpeg capability matrix, enforce lint/type/coverage/package checks, derive the version from one source, and explicitly define/test wheel and sdist contents.

## P2 documentation, contribution, and first-impression gaps

- Documentation is extensive but fragmented across root Markdown files, without a searchable docs site, generated command reference, or generated Python API reference. The wheel does not contain the named CLI docs.
- `README.md` lacks an actual terminal demo/expected output, CI badge, compatibility table, “why this instead of raw FFmpeg/other wrappers” section, architecture overview, and links to changelog/security/contribution policies.
- The live GitHub repository description contradicts CLI-first positioning and has no homepage. The public community profile reports 42% health: no `CONTRIBUTING.md`, Code of Conduct, issue templates, or pull-request template. There is also no `SECURITY.md`, changelog, or Discussions. `main` is not branch-protected.
- `pyproject.toml` exposes Homepage/Repository/Issues only; it lacks Documentation and Changelog URLs.
- The release checklists are useful evidence but are static, dated acceptance notes. They should not substitute for current CI, published artifacts, or a release history.

**Roadmap implication:** after the first real release, consolidate docs into a small task-first site, generate CLI/API references, show a short real demo and expected outputs, publish a transparent support matrix, and add lightweight contribution/security/release governance.

## Suggested repository acceptance sequence

1. Restore cold-start determinism: fixture bootstrap and a package-installed synthetic demo both pass without cache.
2. Fix CLI argument placement, incomplete-group exit codes, and the inert verbose flag; freeze behavior with golden tests.
3. Refactor shared workflows behind typed Python contracts; make CLI/examples thin consumers.
4. Test the promised Python/OS/FFmpeg support matrix and add lint, types, coverage, and artifact-content gates.
5. Publish a signed/tagged package through Trusted Publishing; verify `pipx install pyffmpegcore` from PyPI on three OSes.
6. Only then refresh positioning, demo/docs, contributor paths, and distribution work.

## External primary-source checks

- Public repository: https://github.com/OthmaneBlial/pyffmpegcore
- Last green CI evidence: https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/23687576632
- Empty releases page: https://github.com/OthmaneBlial/pyffmpegcore/releases
- Empty tags page: https://github.com/OthmaneBlial/pyffmpegcore/tags
- Missing PyPI project: https://pypi.org/project/pyffmpegcore/
