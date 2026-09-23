# Development progress

Updated: 2026-09-23

## Current state

- Audit started from `main` at `25adc43150842930f84e25c105a7612f1a4b02f1`, synchronized with `origin/main`.
- Local environment: macOS arm64, Python 3.14.6, FFmpeg/FFprobe 9.0.1.
- Public package version remains `0.2.2`; no new release was created.
- The latest full GitHub CI run for this SHA, [run 35451954201](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35451954201), succeeded, including quality checks, the 80% coverage gate, Python 3.10–3.14 package contracts, and six exact-wheel OS/Python smoke cells.
- No local Docker or container tooling was used.

## Baseline validation

| Check | Result |
| --- | --- |
| `python -m ruff check pyffmpegcore scripts examples tests` | Passed |
| `python -m ruff format --check pyffmpegcore scripts examples tests` | Passed; 134 files already formatted |
| `python -m mypy pyffmpegcore scripts` | Passed; 35 source files |
| `python -m compileall -q pyffmpegcore scripts examples tests` | Passed |
| `python -m pytest` | 363 passed, 7 skipped, 0 failed; 193.20 seconds |
| `python scripts/check_docs.py` | Passed |
| `python -m mkdocs build --strict --clean` | Not run locally: the pinned docs lock requires a `watchdog` binary wheel unavailable for this host. Current-SHA GitHub CI docs job passed. |

After the UTF-8 fix, the full suite passed again: 366 passed, 7 skipped, 0 failed in 139.38 seconds. Ruff, format, mypy, compileall, and `scripts/check_docs.py` passed on the changed tree.

Commands above used the ignored local `.venv` and its pinned CI tools. Initial attempts with `python` failed because that executable is not on this host; `python3` and `.venv/bin/python` are available.

## Architecture and decisions

The repository already follows the intended path: typed workflow input, deterministic plan, preflight, managed execution, output verification, and privacy-aware receipt. CLI, Python, and pipeline adapters converge on the shared planner and workflow engine. Keep these boundaries and avoid broad refactoring without a demonstrated behavior or maintenance problem.

The audit found an inconsistency in the cross-platform text boundary. The managed executor and FFprobe parser decoded tool output as UTF-8 with replacement, but the low-level runner, progress tracker, capability inspection, CLI doctor, and receipt version probe used locale-dependent `text=True`. Those core FFmpeg/FFprobe paths now specify UTF-8 with replacement, and regression tests check the subprocess configuration. This aligns the full package with its documented decoding contract and avoids locale-dependent decode failures.

## Completed in this audit

- Read the current README, roadmap, architecture, security and compatibility policies, package configuration, CI workflows, core execution/probe/receipt paths, and their tests.
- Revalidated the local branch against the remote `main` tip before starting.
- Ran the complete local test and quality baseline above.
- Added explicit UTF-8/replacement decoding to remaining core FFmpeg/FFprobe text subprocess calls and focused tests for runner, progress, capabilities, doctor, and receipt version inspection.

## Remaining work

1. Validate the pushed decoding fix through the hosted CI run and update this record with its exact SHA and result.
2. Continue the still-open items in `ROADMAP.md`, including real-user validation, native package-channel checks, human review of media quality, and a release based on a newly verified artifact.
3. Keep external user/community evidence separate from local or CI evidence. The roadmap's independent-user and public-promotion gates cannot be satisfied by synthetic tests.
4. Do not make the final product video before the roadmap's release and user-validation gates pass.

## Known validation limits

- This local baseline covers one macOS/Python/FFmpeg combination. Cross-platform claims rely on the linked CI matrix, not this run.
- Seven local tests skipped because optional media capabilities or fixtures were unavailable; pytest reported each skip.
- The local strict MkDocs build remains unverified; the current-SHA hosted CI docs job is the available passing evidence.
- No new public package, container, or release was published during this audit.
