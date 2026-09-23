# Development progress

Updated: 2026-09-23

## Current state

- Audit started from `main` at `25adc43150842930f84e25c105a7612f1a4b02f1`, synchronized with `origin/main`.
- Local environment: macOS arm64, Python 3.14.6, FFmpeg/FFprobe 9.0.1.
- Public package version remains `0.2.2`; no new release was created.
- The audit baseline CI for the starting SHA, [run 35451954201](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35451954201), succeeded, including quality checks, the 80% coverage gate, Python 3.10–3.14 package contracts, and six exact-wheel OS/Python smoke cells.
- Core UTF-8 fixes were pushed in `ed83052`; full hosted CI [run 35886966278](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35886966278) passed on that exact SHA.
- Helper-script UTF-8 fixes were pushed in `b70cacf`; full hosted CI [run 35887846148](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35887846148) passed on that exact SHA.
- Directory-image symlink protection was pushed in `167b754`; CI [run 35889125740](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35889125740), CodeQL [run 35889125916](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35889125916), Benchmarks [run 35889125884](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35889125884), and Scorecard [run 35889125847](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35889125847) passed on that exact SHA.
- All six open Dependabot PRs (#15–#20) were closed at the user's request; the open-PR list was verified empty.
- Managed execution now rejects a zero-exit command that failed to create a declared output file; focused local validation passed (20 tests), and hosted CI [run 35890855866](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35890855866) passed on exact SHA `ecf6bc103564ac5c81c1ec3def42c32458f5cd58`.
- Empty declared outputs are now rejected and cleaned up; focused local validation passed (21 tests). Hosted CI [run 35891713418](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35891713418) passed on exact SHA `55d48e368881c4da8d914216b4360bda16625437`.
- Managed workflows now record FFprobe stream/format evidence, fail when FFprobe rejects output, and report `unavailable` with a warning when FFprobe cannot run. The full local suite passed on this implementation (376 passed, 7 skipped); after adding the CLI warning for unverified outputs, 12 focused tests and Ruff, format, and mypy passed.
- The managed-output feature passed full hosted CI [run 35892952944](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35892952944), CodeQL [run 35892953107](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35892953107), Benchmarks [run 35892953006](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35892953006), and Scorecard [run 35892953146](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35892953146) on exact SHA `313543bc1d4957c7ad37fa3a0d9aff5bf0e17b4d`.
- Streamless FFprobe results now have direct regression coverage (7 workflow tests passed locally). Full CI [run 35893651696](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35893651696), CodeQL [run 35893651337](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35893651337), and Scorecard [run 35893651309](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35893651309) passed on exact SHA `98b78e4baecf4b68b00643ed1971b629d4e16e8b`.
- The Container workflow [run 35889125917](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35889125917), triggered by the code push, was cancelled per the no-Docker instruction.
- The Container workflow [run 35890855918](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35890855918), triggered by the output-verification fix, was cancelled per the no-Docker instruction; CodeQL, Benchmarks, and Scorecard passed on `ecf6bc1`.
- The Container workflow [run 35891713312](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35891713312), triggered by the empty-output fix, was cancelled per the no-Docker instruction; CodeQL, Benchmarks, and Scorecard passed on `55d48e3`.
- The Container workflow [run 35892953197](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35892953197), triggered by the FFprobe implementation, was cancelled per the no-Docker instruction. The streamless-test push triggered no Container workflow.
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

After the core UTF-8 fix, the full suite passed again: 366 passed, 7 skipped, 0 failed in 139.38 seconds. Ruff, format, mypy, compileall, and `scripts/check_docs.py` passed on the changed tree. CI run 35886966278 passed build, package matrix, exact-wheel matrix, fuzz, strict docs, and 80% coverage gates. The release/install/benchmark helper follow-up passed 17 focused tests and the same local quality checks. CI run 35887846148 passed distribution build, quality, Python 3.10–3.14 contracts, all six exact-wheel cells, fuzz, strict docs, and the 80% coverage gate on `b70cacf`. The symlink regression test passed with the planning suite (19 passed); Ruff, format, and docs-link checks passed. CI run 35889125740 passed the full matrix and coverage gate on `167b754`.

Commands above used the ignored local `.venv` and its pinned CI tools. Initial attempts with `python` failed because that executable is not on this host; `python3` and `.venv/bin/python` are available.

## Architecture and decisions

The repository already follows the intended path: typed workflow input, deterministic plan, preflight, managed execution, output checks, FFprobe evidence, and privacy-aware receipt. CLI, Python, and pipeline adapters converge on the shared planner and workflow engine. Keep these boundaries and avoid broad refactoring without a demonstrated behavior or maintenance problem. The executor rejects missing or empty declared outputs. Managed workflows record FFprobe format and stream facts, classify unreadable outputs as validation failures, and explicitly flag unavailable FFprobe; the probe checks container metadata and streams but does not decode the full media.

The audit found an inconsistency in the cross-platform text boundary. The managed executor and FFprobe parser decoded tool output as UTF-8 with replacement, but several runner, doctor, capability, receipt, install, release, benchmark, and artifact-build subprocesses used locale-dependent `text=True`. Core FFmpeg/FFprobe paths and the validation helpers now specify UTF-8 with replacement. Regression tests cover those paths. This aligns tool output with the documented decoding contract and avoids locale-dependent decode failures.

The image-directory planner resolved generated output filenames before checking symlinks. A dangling link inside the selected output directory could therefore redirect a write elsewhere; FFmpeg's `-n` does not stop that case. The planner now rejects symlinked generated image destinations before path normalization, with a regression test and a security-model note.

## Completed in this audit

- Read the current README, roadmap, architecture, security and compatibility policies, package configuration, CI workflows, core execution/probe/receipt paths, and their tests.
- Revalidated the local branch against the remote `main` tip before starting.
- Ran the complete local test and quality baseline above.
- Added explicit UTF-8/replacement decoding to remaining core FFmpeg/FFprobe text subprocess calls and focused tests for runner, progress, capabilities, doctor, and receipt version inspection.
- Added the same decoding policy to install, release, benchmark, and artifact-build helpers; all 17 focused helper tests pass.
- Verified hosted CI run 35886966278 succeeded on the exact pushed core-fix SHA `ed83052`.
- Verified hosted CI run 35887846148 succeeded on the exact pushed helper-fix SHA `b70cacf`.
- Reproduced and blocked symlink redirection for generated directory-image outputs; the focused planning suite passed (19 tests).
- Verified hosted CI, CodeQL, Benchmarks, and Scorecard passed on the exact pushed security-fix SHA `167b754`; cancelled its Container run.
- Closed all six Dependabot PRs at the user's request and verified no open PRs remain.
- Reproduced a false success when a zero-exit process omitted its declared output; the shared executor now reports validation failure and regression coverage passes in `tests/test_domain.py`.
- Rejects and removes empty outputs after a zero-exit process; the focused domain tests pass (21 tests).
- Managed workflow results now include FFprobe verification state and stream metadata. Corrupt or streamless outputs fail validation; missing FFprobe remains a warning marked `unavailable` and is visible in human CLI output. Full local suite: 376 passed, 7 skipped; 12 targeted tests passed after the CLI notice.

## Remaining work

1. Continue the still-open items in `ROADMAP.md`, including real-user validation, native package-channel checks, human review of media quality, and a release based on a newly verified artifact.
2. Keep external user/community evidence separate from local or CI evidence. The roadmap's independent-user and public-promotion gates cannot be satisfied by synthetic tests.
3. Do not make the final product video before the roadmap's release and user-validation gates pass.

## Known validation limits

- This local baseline covers one macOS/Python/FFmpeg combination. Cross-platform claims rely on the linked CI matrix, not this run.
- FFprobe verification confirms readable container metadata and at least one media stream; it does not decode every packet or frame.
- Seven local tests skipped because optional media capabilities or fixtures were unavailable; pytest reported each skip.
- The local strict MkDocs build remains unverified; the current-SHA hosted CI docs job is the available passing evidence.
- No new public package, container, or release was published during this audit.
