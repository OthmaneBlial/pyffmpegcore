# PyFFmpegCore Roadmap

> Audit baseline: 2026-08-25, repository `main` at `0e17999`.
>
> This roadmap is ordered by dependency and evidence, not by arbitrary dates. Checkboxes describe future work unless explicitly marked as current evidence. GitHub stars are a possible result of usefulness and trust, not a delivery guarantee.

## Product direction

PyFFmpegCore should become:

> **The safe, explainable FFmpeg task runner for the terminal and CI: preflight the media stack, preview a deterministic plan, run a proven workflow, and keep a machine-readable receipt.**

The current phrase, “a lightweight Python wrapper around FFmpeg/FFprobe,” hides the strongest work already in the repository and puts the project in a crowded category. PyFFmpegCore should not compete with general filter-graph builders, frame-processing libraries, or direct FFmpeg bindings. Its opportunity is to make common media jobs predictable for users who need the power of FFmpeg without memorizing every codec, filter, stream-selection rule, and platform difference.

The primary audience is developers and technical creators running repeatable local or CI media jobs. The Python API remains supported, but the CLI is the primary product surface.

## Evidence-based starting point

### What is already worth keeping

- [x] Fourteen top-level CLI commands/groups and twelve nested actions cover useful video, audio, subtitle, image, inspection, and environment workflows.
- [x] The CLI already has overwrite protection, categorized exit codes, quiet mode, progress reporting, `doctor`, partial JSON output, and shell completion.
- [x] Eleven executable examples are treated as tested contracts.
- [x] The test suite includes real FFmpeg/FFprobe execution and special-character path coverage.
- [x] The last public CI run passed fast checks, real-media checks, and clean-install validation on Linux, macOS, and Windows.
- [x] The package has no third-party runtime Python dependency and produces a wheel and source distribution locally.
- [x] GitHub topics, MIT licensing, secret scanning, push protection, and read-only default Actions permissions are already useful trust foundations.

### What currently blocks adoption

| Priority | Evidence | User consequence |
| --- | --- | --- |
| P0 | The README advertises `pipx install pyffmpegcore`, but the PyPI JSON and Simple endpoints return 404. There is no Git tag or GitHub Release. | The main acquisition path fails before a user can try the product. |
| P0 | The three README badges depend on the nonexistent PyPI project. | The first visible trust signals report “package not found.” |
| P0 | A fresh fixture download now fails because a mutable upstream PNG changed while the pinned checksum did not. | The advertised practice flow and cold-cache real-media validation are not reproducible. |
| P0 | `--verbose` and `--force` placed before a subcommand are overwritten by parser defaults; incomplete command groups exit successfully. | Normal CLI syntax can behave differently from what the user requested, and automation can report false success. |
| P0 | Metadata claims Python 3.8+ through 3.12 while CI exercises only Python 3.12; 3.8 and 3.9 are upstream end-of-life. | Compatibility claims are broader and older than the evidence. |
| P1 | GitHub still describes a lightweight wrapper, the homepage is empty, the README has no real terminal demo, and there is no searchable documentation site. | Visitors cannot quickly see why the project is different or verify the experience. |
| P1 | The CLI is more than 2,200 lines, builds many commands directly, and duplicates workflow logic found in the library and examples. | Fixes and new behavior can drift across three implementations. |
| P1 | The Python API relies heavily on untyped `**kwargs`, raw `CompletedProcess`, inconsistent failures, and unsafe-by-default overwrite behavior. | Library users do not get a discoverable or stable integration contract. |
| P1 | There is no `SECURITY.md`, `CONTRIBUTING.md`, code of conduct, issue form, pull-request template, changelog, CodeQL result, release workflow, or branch protection. GitHub reports a 42% community profile. | Users and contributors have no complete trust, reporting, or participation path. |

Current public traction is a small baseline, not a verdict: 2 stars, 0 forks, no releases, and no external issue activity at audit time. GitHub's latest 14-day owner-visible traffic window reported one unique visitor and three unique cloners; clones may include automation or maintainer activity and must not be treated as users.

## The adoption loop

```text
Working install -> first useful result -> visible proof -> repeatable automation
       -> trustworthy release -> useful issue/recipe -> contributor credit -> discovery
```

Every roadmap phase must strengthen this loop. More commands do not help if install, proof, or trust is broken.

## Guiding product rules

1. **Never advertise an install path that CI cannot reproduce from a public artifact.**
2. **Explain decisions before mutation.** Users should see stream selection, codecs, filters, expected trade-offs, and risks before a job starts.
3. **Use one workflow engine.** CLI commands, Python calls, examples, and pipelines must compile through the same typed plans.
4. **Prefer conservative, tested profiles to “magic” optimization.** Defaults must be inspectable and versioned.
5. **Treat human and machine output as separate contracts.** Human output can improve; JSON schemas and exit behavior require compatibility discipline.
6. **Prove media behavior with real or deterministic fixtures.** Mocked subprocess tests alone are not release evidence.
7. **Keep FFmpeg visible.** PyFFmpegCore should explain the generated argument vector and preserve an expert escape hatch.
8. **Collect no default CLI telemetry.** Use public package/repository signals and opt-in user research.

## Dependency order

```text
P0 Truth and reproducibility
  -> P1 Positioning and first success
    -> P2 Stable workflow engine
      -> P3 Plan, profiles, and receipts
        -> P4 Pipelines and integrations
          -> P5 Sustainable community and distribution
```

---

## P0 — Make the current promise true

**Outcome:** a new user can install a traceable public release, run a correct CLI, and reproduce the basic proof path from a cold machine.

### P0.1 Repair correctness before release

- [x] Fix global argument handling so `pyffmpegcore --force convert ...` and `pyffmpegcore convert --force ...` are equivalent, or document and enforce one syntax with an explicit parser error.
- [x] Give `--verbose` defined, tested behavior or remove it until behavior exists.
- [x] Make incomplete groups such as `pyffmpegcore subtitles` exit with usage code `2` and write the diagnostic to stderr.
- [x] Add golden CLI contract tests covering root/subcommand option placement, nested groups, stdout/stderr separation, exit codes, paths with spaces/apostrophes/Unicode, and overwrite refusal.
- [x] Audit every handler for the stable exit-code categories documented in `CLI_SPEC.md`.
- [x] Ensure the CLI and Python layer both use argument arrays and never interpolate untrusted values through a shell.

**Acceptance gate**

- Every documented option placement is tested through the installed console script.
- Invalid or incomplete invocations never return `0`.
- `--force` never disappears silently and no output is overwritten without an explicit policy.

### P0.2 Make test media deterministic and legally usable

- [x] Replace mutable third-party fixture URLs with tiny redistribution-safe fixtures or deterministic media generated locally with FFmpeg `lavfi` sources.
- [x] Record the origin, license, generator command, codec/container expectations, and SHA-256 for every non-generated fixture.
- [x] Add a true cold-cache CI job that cannot reuse the fixture cache.
- [x] Add a scheduled cold-cache run to detect upstream runner or FFmpeg drift between releases.
- [x] Add a package-installed `pyffmpegcore demo` or `pyffmpegcore smoke-test` that generates a tiny synthetic input, runs one transformation, probes the result, reports success, and cleans up unless asked to retain artifacts.
- [x] Replace hard-coded test counts in prose with a linked CI result or generated compatibility report.

**Acceptance gate**

- A clean checkout with an empty cache can build all required fixtures and pass the documented media smoke path.
- The installed package can demonstrate one complete job without access to `tests/` or the repository checkout.
- No fixture with unknown redistribution rights is included in a release artifact.

### P0.3 Publish a real public beta

- [ ] Confirm the `pyffmpegcore` project name and maintainer account controls in PyPI.
- [x] Single-source the version or enforce equality between package metadata, runtime `__version__`, CLI `--version`, tag, wheel metadata, and release name.
- [x] Add `twine check`, wheel/sdist content checks, clean artifact installation, and README rendering validation.
- [x] Build the wheel and sdist once in an unprivileged job; test those exact files; never rebuild inside the publishing job.
- [ ] Configure a protected GitHub Environment named `pypi` and PyPI Trusted Publishing with narrowly scoped OIDC permissions.
- [ ] Publish the first honest beta from a signed/protected tag only after every earlier P0 gate passes.
- [ ] Create a matching GitHub Release with release notes, compatibility statement, SHA-256 checksums, and links to PyPI attestations.
- [x] Document rollback, yanking, deprecation, and security-fix procedures.
- [x] Replace broken badges immediately; restore PyPI badges only after the public endpoints are healthy. Add the existing CI badge now.

**Acceptance gate**

- `https://pypi.org/pypi/pyffmpegcore/json` returns the intended public version and distributions.
- Clean `pipx install pyffmpegcore` followed by `pyffmpegcore --version`, `doctor`, and `smoke-test` passes on Linux, macOS, and Windows.
- The tag, GitHub Release, PyPI files, checksums, attestations, wheel metadata, and CLI version describe the same immutable release.
- The README contains no failing install command, badge, or top-level link.

### P0.4 Publish only tested support claims

- [x] Adopt an explicit Python policy. The recommended initial public matrix is Python 3.10–3.14; keep an older version only if it has real CI coverage and a stated support reason.
- [x] Run fast/package tests on every claimed Python version.
- [x] Run installed CLI and real-media smoke tests on Linux, macOS, and Windows for a baseline and newest supported Python.
- [x] Capture Python, OS, architecture, FFmpeg, FFprobe, encoder, and filter versions as CI artifacts.
- [x] Define a small FFmpeg compatibility policy and test representative supported builds rather than relying only on the runner's system package.
- [x] Make `requires-python`, classifiers, README, platform notes, docs, and release notes agree.

**Acceptance gate**

- Every claimed Python/OS combination maps to a visible required check.
- The compatibility page separates “tested” from “expected to work” and records the latest verification date.
- No end-of-life Python version remains advertised without deliberate, automated support.

### P0.5 Establish the minimum trust surface

- [ ] Add `SECURITY.md` with supported versions, a private reporting route, scope, and realistic response/disclosure expectations; enable private vulnerability reporting.
- [x] Add `CONTRIBUTING.md`, link it to `DEVELOPMENT.md`, and document fast versus real-media test tiers.
- [x] Add a code of conduct, bug/recipe issue forms, a pull-request template, and support routing.
- [ ] Protect `main` against deletion and force pushes; require stable CI checks before merge.
- [ ] Enable Dependabot alerts, security updates, and weekly updates for Python and GitHub Actions.
- [x] Pin external Actions to full commit SHAs with readable version comments.
- [x] Enable CodeQL and OpenSSF Scorecard reporting; triage the controls, not merely the score.
- [x] Document the command-execution threat model: shell avoidance, filter/path escaping, URL credentials, malicious metadata, temporary files, resource exhaustion, and overwrite policy.

**Acceptance gate**

- GitHub's community profile is complete or each intentional omission is explained.
- A user has a private vulnerability path and a contributor can prepare a conforming PR from repository docs alone.
- Default-branch and release controls are visible, and no untriaged high/critical finding is silently accepted.

---

## P1 — Make the value obvious and the first success fast

**Outcome:** a qualified visitor understands the project in seconds and completes a useful task from the public artifact in under five minutes.

### P1.1 Align the public story

- [x] Use one category statement across GitHub description, README, PyPI summary, docs, and release notes.
- [x] Replace the generic “wrapper” framing with the safe, explainable task-runner promise.
- [ ] State the primary user, supported environment, required external FFmpeg dependency, and explicit limits above the fold.
- [x] Add a short “When to use PyFFmpegCore / when not to” comparison against raw FFmpeg, `ffmpeg-python`, `python-ffmpeg`, `ffmpegio`, and PyAV.
- [x] Keep the comparison factual: PyFFmpegCore is for task safety and reproducibility, not arbitrary graph DSLs, async builders, NumPy frame I/O, or direct packet/frame access.
- [x] Set the GitHub homepage to the documentation site and add Documentation/Changelog project URLs to package metadata.

### P1.2 Build a proof-led README

- [ ] Put one working install command, one representative task, expected output, and the support matrix above the long command catalog.
- [ ] Record a real 60–90 second terminal demo: public install, `doctor`, synthetic smoke test, explained plan, progress, output summary, and receipt. Do not fake terminal output.
- [ ] Provide accessible text steps and alt text for every visual asset.
- [ ] Show one measurable before/after result, such as file size, format, streams, or loudness—not decorative screenshots.
- [ ] Move the complete command catalog to docs and keep three high-value recipes in the README.
- [ ] Surface real proof: current CI, compatibility matrix, release provenance, security policy, and real-media methodology.

### P1.3 Create task-first documentation

- [x] Publish searchable docs with installation, five-minute start, CLI reference, Python API reference, recipes, troubleshooting, exit codes, JSON schemas, compatibility, changelog, security, and migration notes.
- [x] Generate CLI reference from the parser and Python API reference from the public typed layer to prevent drift.
- [x] Add recipe pages organized by user outcome: web-compatible video, exact-size upload, audio extraction, podcast normalization, subtitles, thumbnails, and image batches.
- [x] Add copy-paste examples for Bash, PowerShell, and Python where behavior differs.
- [x] Run documentation build, link, code-snippet, and package-install checks in CI.

**P1 acceptance gate**

- Five external usability attempts are observed; at least four users complete install, diagnosis, and one task in under five minutes without maintainer intervention.
- Every above-the-fold command is executed from a built/public artifact in CI.
- All badges, links, code snippets, expected outputs, and accessibility alternatives pass automated checks.
- The public repository description and README no longer contradict the CLI-first product direction.

---

## P2 — Build one stable workflow engine

**Outcome:** CLI, Python, examples, and future pipelines share a typed, inspectable, compatibility-conscious core.

### P2.1 Separate parsing, planning, execution, and presentation

- [ ] Split the monolithic CLI into command registration, input validation, workflow planning, execution, and human/JSON rendering modules.
- [ ] Move every FFmpeg command builder out of CLI handlers and examples into shared workflow services.
- [ ] Make examples thin consumers of the same public layer used by the CLI.
- [ ] Preserve a low-level `run(args)` escape hatch without letting it bypass safety defaults silently.

### P2.2 Replace weak public contracts

- [ ] Replace public `**kwargs` bags with typed option models whose unsupported fields fail immediately.
- [x] Introduce stable domain types such as `MediaInfo`, `StreamInfo`, `ExecutionPlan`, `JobResult`, `ProgressEvent`, and categorized exceptions.
- [ ] Return a stable result containing command, status, elapsed time, stdout/stderr policy, warnings, and output metadata instead of exposing only `CompletedProcess`.
- [ ] Use explicit overwrite, timeout, cancellation, temporary-file, and cleanup policies in both CLI and Python.
- [x] Add raw and simplified FFprobe modes; preserve tags, dispositions, chapters, stream language, rotation, color/HDR metadata, and attachments where relevant.
- [x] Ensure custom FFmpeg and FFprobe paths propagate through every workflow, including target-size compression.
- [x] Define a deprecation policy before declaring the Python layer stable.

### P2.3 Make quality evidence continuous

- [x] Add formatting/linting, static typing, coverage measurement, package metadata validation, and artifact-content checks.
- [x] Define a meaningful coverage threshold by risk area; do not optimize only for a headline percentage.
- [ ] Test stream selection, metadata preservation, corrupted inputs, missing codecs/filters, full disks, interruption, timeouts, and cleanup.
- [ ] Generate tiny media permutations for video-only, audio-only, multi-audio, subtitles, chapters, cover art, rotation, variable frame rate, and Unicode metadata.
- [ ] Decide whether the sdist is a runtime source artifact or a self-contained testable source artifact, then enforce its exact contents.

**P2 acceptance gate**

- No shipped workflow constructs its command independently in the CLI or examples.
- Public types are documented, statically checked, and covered by compatibility tests.
- CLI human output may evolve, while versioned JSON, result types, exit codes, overwrite behavior, and deprecations have contract tests.
- Failure paths leave no misleading success code, partial output presented as complete, or orphaned pass/temporary files.

---

## P3 — Ship the signature experience: preflight → plan → run → receipt

**Outcome:** PyFFmpegCore offers a distinctive workflow that makes FFmpeg operations inspectable and reproducible instead of merely shorter.

### P3.1 Capability-aware preflight

- [x] Expand `doctor` beyond executable presence to inventory required encoders, decoders, filters, muxers, protocols, subtitle support, and hardware accelerators.
- [x] Preflight each job against input streams, output/container compatibility, disk space, write permissions, collisions, and installed FFmpeg capabilities.
- [x] Explain the exact missing capability and provide a tested fallback or an OS-specific remedy when one exists.
- [x] Produce the same preflight facts as readable text and versioned JSON.
- [ ] Maintain a capability-rules catalog keyed by workflow and test it across the supported FFmpeg matrix.

### P3.2 Deterministic plans and explanations

- [x] Add non-mutating `--dry-run` and `--explain` support to every writing command.
- [x] Represent the exact argument vector as a JSON array; show a safely escaped display form without executing through a shell.
- [x] Explain selected streams, copied/re-encoded/dropped data, codecs, filters, quality/size trade-offs, hardware fallback, overwrite policy, and expected outputs.
- [ ] Use FFmpeg structured interfaces such as progress and graph output when the installed version supports them, with tested fallbacks for older versions.
- [x] Make plans deterministic and snapshot-testable after normalizing paths and environment-specific values.

### P3.3 Curated workflow profiles

- [x] Ship a small profile registry instead of dozens of thin commands. Initial candidates: `web/mp4-compatible`, `web/small-upload`, `audio/podcast-speech`, `subtitles/accessibility`, and `archive/mezzanine`.
- [x] Add `profile list`, `profile show`, and `profile validate` commands explaining every choice and required capability.
- [x] Version profile behavior so upgrades never silently change an output contract.
- [x] Support project/user profiles only through a documented versioned schema with strict validation.
- [x] Keep service-specific presets out of the core unless their requirements are stable, sourced, and maintained.
- [ ] Turn target-size compression into an excellent “fit this file under a limit” workflow with human size units, quality floors, honest feasibility errors, and before/after proof.

### P3.4 Privacy-aware run receipts

- [ ] Add optional versioned JSON receipts containing the plan, tool versions, normalized progress summary, elapsed time, exit category, warnings, and input/output probe summaries.
- [ ] Redact URL credentials, secrets, and private path components by default; document the redaction policy with adversarial tests.
- [ ] Make content hashing opt-in for large or private files and record the hash algorithm explicitly.
- [ ] Add a receipt validation command and a bug-report flow that attaches `doctor --json` plus a redacted receipt without requiring private media.
- [ ] Publish the schema, examples, compatibility rules, and migrations.

**P3 acceptance gate**

- A user can diagnose, preview, execute, and validate a documented job in under five minutes.
- Every writing command has a non-mutating deterministic plan and machine-readable result.
- Every shipped profile has golden real-media contracts across the documented environment matrix.
- Unsupported capabilities fail before mutation with a useful remedy or tested fallback.
- Receipts reproduce enough context to diagnose a fixture-based issue while leaking no default credential or sensitive absolute path.

---

## P4 — Add reliable local and CI automation

**Outcome:** repeated and multi-step media work becomes resumable, observable, and portable without turning PyFFmpegCore into a hosted transcoding platform.

### P4.1 A common job and batch model

- [ ] Generalize image batches into a common job model for mixed media with bounded concurrency and explicit resource limits.
- [ ] Emit JSON Lines progress events and per-item receipts with stable partial-success semantics.
- [ ] Add retry policies for classified transient failures, interruption handling, and resume from a manifest.
- [ ] Prevent accidental output collisions and duplicate work across spaces, apostrophes, Unicode, corrupt inputs, and mixed extensions.
- [ ] Never retry deterministic validation or unsupported-capability failures blindly.

### P4.2 Declarative pipelines

- [ ] Define a versioned TOML/JSON pipeline schema that composes existing typed workflows rather than raw shell strings.
- [ ] Add whole-pipeline preflight, dry-run, dependency visualization, cancellation, resume, and optional content-aware caching.
- [ ] Include tested pipelines for “web publish,” “podcast package,” and “video plus thumbnails/subtitles.”
- [ ] Keep secrets outside pipeline files and redact them from plans, logs, cache keys, and receipts.
- [ ] Add schema migration tools before breaking the first stable pipeline format.

### P4.3 Distribution integrations after the contract stabilizes

- [ ] Publish a pinned, multi-architecture GHCR image containing a documented FFmpeg build only after licensing, codec, update, SBOM, and vulnerability-maintenance review.
- [ ] Offer a GitHub Action that runs a versioned pipeline and uploads receipts/output artifacts; pin the container and action by digest/SHA.
- [ ] Document `pipx` and `uv tool install`; consider a Homebrew tap only after public demand is measured.
- [ ] Benchmark startup, processing overhead, artifact size, and cache behavior against raw FFmpeg. PyFFmpegCore must add negligible orchestration overhead.

**P4 acceptance gate**

- An interrupted batch resumes without reprocessing completed outputs and reports deterministic partial success.
- The same example pipeline passes locally, in the container, and in the GitHub Action with equivalent normalized receipts.
- Images/actions have SBOMs, provenance, update ownership, and no unresolved high/critical vulnerability.
- Integrations are released only when their ongoing maintenance burden has an owner.

---

## P5 — Build sustainable discovery and contribution loops

**Outcome:** useful releases generate proof, recipes, feedback, and credited contributions that bring the right users back.

### P5.1 Turn support into public knowledge

- [ ] Convert repeated real user questions into tested recipes and troubleshooting pages.
- [ ] Publish before/after media evidence and receipts for each flagship recipe.
- [ ] Invite recipe proposals through a structured issue form; promote only validated recipes into the supported catalog.
- [ ] Enable Discussions for recipe requests/show-and-tell only when the maintainer can triage it consistently.
- [ ] Link releases to the exact recipes, compatibility evidence, and user problems they improve.

### P5.2 Make first contributions genuinely bounded

- [ ] Create at least five scoped newcomer issues with file pointers, acceptance criteria, and verification commands before inviting contributions.
- [ ] Provide a contribution ladder: docs/recipes → fixtures/tests → platform support → workflow/core changes.
- [ ] Add labels for `good first issue`, `help wanted`, `recipe`, `documentation`, `platform`, `bug`, and `security` with clear meanings.
- [ ] Credit external issue authors, testers, recipe contributors, and code contributors in release notes.
- [ ] Publish realistic triage and review expectations; do not create an abandoned community surface.

### P5.3 Distribute proof, not hype

- [ ] Share releases in relevant Python, FFmpeg, creator-tooling, and CI communities with a reproducible use case and clear project affiliation.
- [ ] Publish short technical notes on capability preflight, exact-size compression, deterministic plans, and privacy-safe receipts.
- [ ] Maintain an honest comparison page and update it when competitor behavior changes.
- [ ] Ask users for the workflow they completed and friction encountered, not merely for a star.
- [ ] Never use star exchanges, mass unsolicited posting, fake benchmarks, or unverified “fastest/easiest/secure” claims.

**P5 acceptance gate**

- Each release has a tag, PyPI artifact, attestation, changelog entry, compatibility evidence, one demonstrated workflow, and contributor credit.
- At least one external user completes the five-minute flow without maintainer intervention before broad promotion.
- External issues and pull requests receive a response within the published service level during active maintenance periods.
- Repeat contributors, dependent repositories, recipe reuse, and qualified referrers grow alongside stars rather than being replaced by them.

---

## First implementation issues, in order

These are the first repository issues to create after reviewing this roadmap:

1. **Fix CLI global-option precedence and nested-group exit codes.**
2. **Replace the drifted media fixture flow with deterministic/licensed fixtures and a cold-cache check.**
3. **Add an installed synthetic `smoke-test` command.**
4. **Align and test the Python support matrix.**
5. **Create the Trusted Publishing release pipeline and artifact integrity gates.**
6. **Add security, contribution, issue, PR, changelog, and branch-protection foundations.**
7. **Rewrite the repository hero around the safe, explainable task-runner promise and record a real terminal demo.**
8. **Extract typed workflow plans from the monolithic CLI and remove duplicated command construction.**
9. **Ship versioned preflight and `--dry-run` JSON schemas.**
10. **Ship privacy-aware execution receipts and the first three proven profiles.**
11. **Generalize resumable batches only after plan/receipt contracts are stable.**
12. **Add container and GitHub Action distribution only after licensing and maintenance gates pass.**

## Measurement scorecard

Stars belong in the last row because they measure advocacy, not whether the product works.

| Funnel stage | Primary measure | Required guardrail |
| --- | --- | --- |
| Discovery | Unique GitHub/docs visitors and qualified referrers | Do not infer demand from clone count alone. |
| Activation | Successful public-artifact install and completion of the first task | Never count editable-checkout CI as public install proof. |
| First value | Median time from install command to verified output | Measure with external users and include FFmpeg setup friction. |
| Trust | Green support matrix, working links, attested releases, security triage | Never claim a version/platform that required checks do not exercise. |
| Usefulness | Completed recipes, repeat use, actionable workflow issues, dependent repositories | PyPI downloads include bots, mirrors, and CI; report them carefully. |
| Contribution | Unique external issue/PR authors, merged external PRs, repeat contributors, review time | Exclude maintainer and bot activity from community growth. |
| Advocacy | Organic stars, forks, mentions, return visitors, recommendations | Never make a star target an engineering acceptance criterion. |

### Launch gates

- **Gate A — Install:** every advertised installation path works from the public release.
- **Gate B — Proof:** supported environments and flagship workflows have current visible evidence.
- **Gate C — Trust:** release provenance, security reporting, and contribution paths are complete.
- **Gate D — Differentiation:** preflight, plan, profiles, and receipts work end to end.
- **Gate E — External activation:** independent users complete the first-value journey and their friction is incorporated.

## Explicit non-goals

- Replacing the complete FFmpeg option surface.
- Building another arbitrary filter-graph DSL.
- Competing with PyAV for packet/frame-level native access or with scientific libraries for NumPy/Pillow frame I/O.
- Using async callbacks as the headline differentiator; job control should serve reliable cancellation, progress, and resumption.
- Adding dozens of one-flag commands before the existing product is installable and stable.
- Bundling or auto-downloading FFmpeg in the Python wheel before licensing, codec, integrity, platform, size, and security-update obligations are solved.
- Building a GUI, cloud transcoding service, plugin marketplace, or AI command generator without validated demand.
- Enabling telemetry by default, promising virality, or optimizing for a vanity star milestone.

## Decision rules for later requests

A proposed feature enters the committed roadmap only when it has:

1. a named user and concrete job;
2. evidence from an issue, interview, recipe usage, or repeated support need;
3. a place in the shared workflow engine rather than a second implementation;
4. a preflight rule, deterministic plan, safe failure behavior, and receipt contract;
5. real/deterministic media fixtures and compatibility acceptance criteria;
6. documentation and a maintainer for its release surface.

Hardware acceleration, streaming/HLS/DASH, standalone executables, service-specific presets, native bindings, and GUI work stay in the evidence backlog until these conditions are met.

## Primary research references

### PyFFmpegCore evidence

- [Repository](https://github.com/OthmaneBlial/pyffmpegcore)
- [Last successful CI run](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/23687576632)
- [GitHub Releases](https://github.com/OthmaneBlial/pyffmpegcore/releases)
- [PyPI JSON endpoint](https://pypi.org/pypi/pyffmpegcore/json) — returned 404 at audit time

### Packaging, release, and trust guidance

- [PyPA: publishing package distributions with GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [PyPI digital attestations](https://docs.pypi.org/attestations/)
- [CPython supported versions](https://devguide.python.org/versions/)
- [GitHub community profile guidance](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories)
- [GitHub Actions secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use)
- [OpenSSF Scorecard checks](https://github.com/ossf/scorecard/blob/main/docs/checks.md)

### Positioning references

- [`ffmpeg-python`](https://github.com/kkroening/ffmpeg-python): arbitrary FFmpeg filter graphs and command compilation
- [`python-ffmpeg`](https://github.com/jonghwanhyeon/python-ffmpeg): fluent synchronous/asynchronous execution and progress events
- [`ffmpegio`](https://github.com/python-ffmpegio/python-ffmpegio): broad executable-based media, stream, filter, and array integration
- [PyAV](https://github.com/PyAV-Org/PyAV): direct container, packet, codec, and frame access
- [FFmpeg and FFprobe documentation](https://ffmpeg.org/documentation.html): authoritative engine and structured interfaces

Detailed audit notes and source limitations are stored in [`research_pyffmpegcore_roadmap/`](research_pyffmpegcore_roadmap/).
