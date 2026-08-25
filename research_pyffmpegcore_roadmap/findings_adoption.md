# Track 3 — GitHub adoption, trust, distribution, and contribution

Audit date: 2026-08-25 (Europe/Paris)

## Executive diagnosis

PyFFmpegCore does not primarily have a feature-count problem. It has a trust-and-conversion gap between a promising repository and an installable, releasable open-source product.

The strongest current asset is real validation: the repository has 105 tests, checksum-pinned media fixtures, end-to-end media checks, a successful multi-OS CLI install workflow, and a read-only default GitHub Actions token. Those are better foundations than many young wrappers have.

The most serious issue is that the public promise is not currently true: the README tells users to run `pipx install pyffmpegcore` and displays three PyPI-derived badges, but both the PyPI JSON API and Simple API return 404 for `pyffmpegcore`. There is also no Git tag and no GitHub Release. A visitor who tries the primary install path cannot reach first success, and broken trust badges amplify the failure.

The next bottlenecks are incomplete compatibility proof, a 42% GitHub community profile, and absent release/security automation. These should be fixed before adding a large number of commands or promoting the project. None of this can guarantee virality or a star count; it can make discovery convert into genuine use, trust, contributions, and repeat attention.

## Evidence snapshot

| Area | Current evidence | Consequence |
| --- | --- | --- |
| Public traction | The GitHub API reports 2 stars, 0 forks, 0 subscribers, 0 open issues, and a single contributor. The repository page reports 60 commits. Authenticated traffic for the latest 14-day window reports 1 unique visitor and 3 unique cloners; clones should not be treated as verified users because automation and the owner can contribute to them. | There is not yet evidence of an organic acquisition loop. Optimize activation and contribution before interpreting stars as product-market fit. |
| Freshness | The last public push and last successful CI run were 2026-03-28, nearly five months before this audit. OpenSSF treats visible maintenance activity as a trust signal, although a quiet utility is not necessarily abandoned. | Publish an honest support policy and a sustainable release/triage cadence rather than manufacturing commits. |
| Distribution | `pyproject.toml` and `pyffmpegcore.__version__` say `0.1.2`, but there are no Git tags, GitHub Releases, PyPI JSON record, or PyPI Simple index entry. The README's PyPI badges and `pipx`/`pip` commands therefore lead to a nonexistent distribution. | This is the P0 launch blocker. The repository is buildable but not publicly consumable through its advertised primary channel. |
| CI and install proof | The latest GitHub Actions run passed. CI builds distributions, runs non-media tests, runs selected real-media tests, and validates clean CLI installs on Linux, macOS, and Windows. Internet fixtures are pinned by SHA-256. | Keep this as the core proof story; surface it in the README and release evidence. |
| Python support | Metadata claims Python `>=3.8` and classifiers cover 3.8–3.12, while CI tests only 3.12. CPython 3.8 and 3.9 are end-of-life; supported stable branches on the audit date are 3.10–3.14. | The published compatibility claim would be both under-tested and stale. Choose a policy, then make metadata, docs, and a version matrix agree. |
| Repository presentation | The topic set is already strong and relevant. However, the GitHub homepage URL is empty, the README has no visual terminal demo or live documentation link, and its only badges depend on the absent PyPI project. | Discovery metadata is partly good, but the above-the-fold trust surface currently fails. |
| Community readiness | GitHub's community profile API reports 42%. It finds README and LICENSE but no `CONTRIBUTING.md`, code of conduct, issue template, or pull-request template. Discussions are disabled and blank issues are allowed. `DEVELOPMENT.md` is useful but is not a substitute for GitHub's recognized contribution entry point. | A potential contributor gets no scoped entry path, behavioral expectations, issue schema, or review contract. |
| Repository security | Secret scanning and push protection are enabled, and CI declares `contents: read`. Dependabot security updates are disabled; the default branch is unprotected; no CodeQL analysis exists; no `SECURITY.md` exists; actions are referenced by mutable major tags; and no OpenSSF Scorecard result exists for the repository. | Good token and secret basics exist, but vulnerability intake, update automation, static analysis, workflow integrity, and merge protection remain incomplete. |
| Release integrity | The project can build a wheel and sdist and calculate SHA-256 digests locally, but it has no publishing workflow, protected `pypi` environment, Trusted Publisher, public attestations, release checksums, or release notes. | Users cannot connect source, tag, CI result, package, and provenance into one verifiable release chain. |
| Packaging metadata | Metadata includes description, license, keywords, classifiers, homepage/repository/issues, and a console entry point. It lacks well-known Documentation and Changelog URLs. The version is duplicated in `pyproject.toml` and `pyffmpegcore/__init__.py`. The project uses the modern PEP 639 string license form but allows `setuptools>=61.0`; PyPA lists setuptools 77.0.3 as the first release supporting that form. | The eventual PyPI page will be less navigable, duplicated version state creates avoidable release drift, and the declared build-system floor does not guarantee support for the declared license metadata. |
| Quality gates | Coverage configuration exists, but CI does not measure or enforce coverage. CI also has no lint/type/static quality gate and does not validate the rendered PyPI description before publish. | The test count is credible, but visitors cannot see breadth or regression thresholds, and a malformed package page could reach release. |

Current-state sources:

- [GitHub repository](https://github.com/OthmaneBlial/pyffmpegcore)
- [GitHub repository API](https://api.github.com/repos/OthmaneBlial/pyffmpegcore)
- [GitHub community-profile API](https://api.github.com/repos/OthmaneBlial/pyffmpegcore/community/profile)
- [GitHub releases API](https://api.github.com/repos/OthmaneBlial/pyffmpegcore/releases)
- [Latest successful CI run](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/23687576632)
- [Authenticated GitHub clone-traffic endpoint](https://api.github.com/repos/OthmaneBlial/pyffmpegcore/traffic/clones)
- [Authenticated GitHub view-traffic endpoint](https://api.github.com/repos/OthmaneBlial/pyffmpegcore/traffic/views)
- [PyPI JSON endpoint for `pyffmpegcore`](https://pypi.org/pypi/pyffmpegcore/json) (404 at audit time)
- [PyPI Simple endpoint for `pyffmpegcore`](https://pypi.org/simple/pyffmpegcore/) (404 at audit time)

## Recommended roadmap inputs

### P0 — Make the advertised install path real

Outcome: a visitor can move from the README to a verified CLI invocation from a public, traceable release.

Deliverables:

1. Reserve/create the `pyffmpegcore` PyPI project through a pending Trusted Publisher, after confirming the name and account controls in the PyPI UI.
2. Add a tag-triggered release workflow with three separate responsibilities:
   - build the wheel and sdist once;
   - inspect and install those exact artifacts in a clean environment;
   - publish the already-built artifacts, without rebuilding in the privileged publish job.
3. Use a protected GitHub Environment named `pypi`, require manual approval, grant only `id-token: write` to the publish job, and use PyPI Trusted Publishing instead of a long-lived API token.
4. Publish with the official `pypa/gh-action-pypi-publish` action. It produces PyPI attestations by default, tying each file to the publishing workflow identity.
5. Create a matching Git tag and GitHub Release with concise release notes, compatibility statement, checksums, and links to the PyPI files and attestations.
6. Remove or replace all PyPI-dependent badges until the project exists. After publication, add working CI, PyPI version, supported Python, license, and provenance links without turning the README into a badge wall.
7. Make the release version single-sourced or add a CI check that `pyproject.toml`, runtime `__version__`, Git tag, wheel metadata, and CLI `--version` are identical.
8. Raise the build-system requirement to `setuptools>=77.0.3` if retaining the PEP 639 `license = "MIT"` form, declare `license-files = ["LICENSE"]`, and test an isolated build against the declared minimum backend.

Acceptance criteria:

- `https://pypi.org/pypi/pyffmpegcore/json` returns 200 and lists the intended wheel and sdist.
- A clean `pipx install pyffmpegcore` succeeds on Linux, macOS, and Windows, followed by `pyffmpegcore --version` and `pyffmpegcore doctor`.
- Installing the wheel downloaded from PyPI, rather than from the checkout, passes the packaged CLI smoke test.
- The Git tag, GitHub Release, PyPI version, package metadata, and CLI version are identical.
- Every published distribution exposes a PyPI provenance/attestation record.
- The README contains no installation command or badge that fails from a clean machine.

Primary guidance:

- [PyPA guide to GitHub Actions publishing](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [PyPI digital attestations](https://docs.pypi.org/attestations/)
- [PyPI attestation production](https://docs.pypi.org/attestations/producing-attestations/)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)

### P0 — Align support claims with current Python reality

Outcome: compatibility is a tested contract rather than an optimistic classifier list.

Recommended policy: raise the supported floor to Python 3.10 and test 3.10, 3.11, 3.12, 3.13, and 3.14. If maintaining 3.8 or 3.9 is a deliberate user requirement, keep them only with explicit CI coverage and an announced end date; both versions are already end-of-life upstream.

Deliverables:

- Add a Linux unit/package matrix for every supported Python version.
- Keep full clean-install/media coverage on all three operating systems for at least one baseline Python and the newest stable Python. A full OS × Python × media matrix is unnecessary if it makes feedback too slow.
- Record `python`, `ffmpeg`, and `ffprobe` versions in CI artifacts so the compatibility statement is reproducible.
- Update `requires-python`, classifiers, README, install docs, platform notes, and release notes from the same support policy.
- Add a scheduled compatibility run so upstream FFmpeg and runner-image changes are detected between releases.
- Add a built-distribution check that validates metadata/rendering and installs from the wheel and sdist, not only editable source.

Acceptance criteria:

- Every claimed Python version has a green required status check.
- Linux, macOS, and Windows each install the public-style artifact and execute a real media task.
- No end-of-life Python is claimed unless it is intentionally tested and documented.
- The README compatibility table links to the CI workflow and names the latest verified date and tool versions.

Primary guidance:

- [Current CPython version status](https://devguide.python.org/versions/)
- [PyPA `pyproject.toml` guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [PyPA project metadata specification](https://packaging.python.org/specifications/declaring-project-metadata/)

### P0 — Establish a minimum public trust and contribution surface

Outcome: users know how to get help or report a vulnerability, and contributors know how to make an acceptable change.

Deliverables:

- Add `SECURITY.md` with supported versions, what qualifies as a vulnerability, a private reporting path, acknowledgement expectations, and an initial response/disclosure timeline. Enable GitHub private vulnerability reporting if it is currently off.
- Add `CONTRIBUTING.md` that points to `DEVELOPMENT.md` and covers environment setup, fixture-download implications, test tiers, formatting/type checks, commit/PR expectations, and how to add a command without shell-injection or path-handling regressions.
- Add a standard code of conduct and an enforcement contact.
- Add issue forms for bug reports and feature/recipe proposals. Require OS, Python version, FFmpeg/FFprobe versions, `doctor --json` output with a warning to redact private paths, minimal command, expected/actual behavior, and a tiny reproducible input when licensing permits.
- Add a pull-request template with tests, documentation, compatibility impact, security review, and media-fixture licensing/checksum items.
- Add a support/configuration file that routes usage questions away from security reports. Enable Discussions only if the maintainer commits to triage it; an abandoned forum is worse than a clear issue policy.
- Create a small, curated backlog with `good first issue`, `help wanted`, `documentation`, `bug`, `platform`, and `security` labels. Each newcomer issue should state file pointers, acceptance criteria, and test commands.

Acceptance criteria:

- GitHub's community profile reaches 100% or every intentionally omitted item has a documented reason.
- A new contributor can set up, run the fast suite, identify the real-media suite, and open a conforming PR using only repository documentation.
- Vulnerability reporters have a private channel; public bug templates explicitly redirect security reports.
- At least five genuinely bounded newcomer issues exist before asking people to contribute.

Primary guidance:

- [GitHub community profiles](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories)
- [GitHub contribution guidelines](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors)
- [GitHub repository best practices](https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories)

### P1 — Harden the repository and release supply chain

Outcome: a package consumer can see that changes, automation, and releases are protected by explicit controls.

Deliverables, in dependency order:

1. Protect `main`: block force pushes and deletion and require the stable CI checks before merge. Require PRs for changes. For a solo-maintainer repository, introduce mandatory external approval only when a reliable second maintainer exists; do not create a permanent merge deadlock.
2. Enable Dependabot alerts and security updates. Add weekly version updates for both `pip` and `github-actions` ecosystems.
3. Pin third-party actions to full commit SHAs and keep readable version comments. Dependabot can maintain those references. Current `@v4`/`@v5` references are mutable tags.
4. Keep the existing top-level `contents: read` default. Grant `id-token: write` only inside the PyPI publish job; avoid repository write permissions in build/test jobs.
5. Enable CodeQL default setup for Python and add the OpenSSF Scorecard workflow/SARIF upload. The public Scorecard API currently has no result for this repository.
6. Add `CODEOWNERS` for `.github/workflows/`, release configuration, and package metadata once a second maintainer can review these sensitive paths.
7. Attach generated SHA-256 checksums to each GitHub Release. Add an SPDX or CycloneDX SBOM as a P2 release artifact; the runtime dependency set is currently empty, so provenance and safe release automation have higher immediate value.
8. Document the command-execution threat model: no shell interpolation, argument lists by default, safe overwrite behavior, subtitle/filter path handling, untrusted metadata, URL/protocol inputs, and temporary-file cleanup. Add regression tests around those boundaries.

Acceptance criteria:

- The default branch rejects force pushes, deletion, and merges with failed required checks.
- Dependabot alerts/security updates and action-version updates are enabled and triaged.
- Every external action reference uses a full SHA; automated updates remain reviewable.
- CodeQL and Scorecard produce visible results, with no unresolved high/critical finding accepted silently.
- Build/test jobs remain read-only; only the isolated publish job can request OIDC.
- Every release has attestations and checksums traceable to the tagged source.

Primary guidance:

- [GitHub repository security baseline](https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories#secure-your-repository)
- [GitHub security quickstart](https://docs.github.com/en/code-security/getting-started/quickstart-for-securing-your-repository)
- [GitHub Actions secure-use reference](https://docs.github.com/en/actions/reference/security/secure-use)
- [OpenSSF Scorecard checks and remediation](https://github.com/ossf/scorecard/blob/main/docs/checks.md)

### P1 — Redesign the repository page for activation, not volume

Outcome: the first screen answers what it does, why it is preferable for a specific task, whether it works on the visitor's machine, and how to try it safely.

Deliverables:

- Replace the current generic repository description with the clearest defensible differentiator discovered by the product/competitive tracks. Keep CLI-first positioning consistent across the GitHub description, README, package summary, and documentation.
- Add a short, real terminal recording near the top: install, `doctor`, one representative command, progress, and verified output. Keep it accessible with text alternatives and do not fake output.
- Rebuild the README's first screen around: one-line promise, visual proof, working install, one copy-paste success path, CI/release trust signals, and links to recipes/API/security/contributing.
- Add an honest support table for OS, Python, and tested FFmpeg versions. Separate “tested” from “expected to work.”
- Add a concise “why not raw FFmpeg / when not to use this” section. State that advanced FFmpeg users may prefer raw commands and that the wrapper does not bundle FFmpeg.
- Move the long command catalog into a documentation site or task-based recipes, leaving a small set of high-value examples in the README.
- Publish searchable documentation with CLI reference, Python API reference, recipes, troubleshooting, exit codes/JSON schemas, compatibility, changelog, and migration notes.
- Set the GitHub homepage URL to the documentation or project site. Add well-known `Documentation` and `Changelog` keys under `[project.urls]` so PyPI exposes them prominently.
- Add a CI badge immediately; add the PyPI badge only after launch. A coverage badge should appear only after a meaningful threshold is measured and enforced.

Acceptance criteria:

- A new visitor can understand the primary user and complete one task from the README in under five minutes.
- Every above-the-fold command is continuously tested from a built/public artifact.
- Every badge and top-level link returns success and points to current evidence.
- GitHub description, homepage, topics, README, PyPI summary, and docs use the same positioning.
- Documentation build/link checks run in CI.

### P1 — Turn releases and contributions into repeatable distribution loops

Outcome: each meaningful release produces a useful artifact, evidence, documentation, and a reason for users and contributors to return.

Deliverables:

- Add `CHANGELOG.md` with user-visible changes, compatibility notes, deprecations, and security fixes. Link it through package metadata.
- Define a light release cadence based on completed value, not arbitrary weekly version inflation. Use pre-releases for risky CLI/API changes.
- Publish release notes with one demonstrable workflow, before/after evidence, compatibility, upgrade instructions, contributor credits, and a small next-contribution list.
- Convert recurring support questions into tested recipes and link the contributor who supplied the use case.
- Use Discussions for recipe requests/show-and-tell only after triage capacity exists; periodically promote validated recipes into docs/tests.
- Maintain a visible “good first contribution” path: docs/recipe tasks first, then tests/platform support, then command/API work.
- Credit all contributors in release notes. Make review and first-response expectations visible and realistic.
- Share releases only in relevant Python/FFmpeg communities with reproducible examples and clear disclosure; do not run mass-posting or star-exchange campaigns.

Acceptance criteria:

- Every release has a tag, GitHub Release, PyPI artifact, attestation, changelog entry, and green compatibility checks.
- The median first maintainer response to a valid issue/PR is under 72 hours during active release periods, or the repository publishes a different realistic service level.
- Track unique external issue authors, PR authors, merged external PRs, repeat contributors, and recipe reuse. Do not count owner activity as community growth.
- At least one release note or recipe per cycle demonstrates real input and verifiable output.

## Measurement framework

Use a small funnel that distinguishes real use from vanity metrics:

| Stage | Primary measure | Guardrail |
| --- | --- | --- |
| Discovery | Unique GitHub visitors, documentation entrances, qualified referrers | Do not infer demand from clone count alone. |
| Activation | Successful clean installs and completion of the README's first task | The command must use the public artifact, not an editable checkout. |
| Trust | Green supported-version matrix, working links, 100% community profile, attested releases, zero untriaged high/critical security alerts | Never claim an OS/Python/FFmpeg version that CI does not exercise. |
| Usefulness | PyPI downloads after filtering obvious CI/mirror noise where possible, recipe usage, issue reports containing real workflows | Downloads are not active users and should not be used alone. |
| Contribution | Unique external issue/PR authors, merged external PRs, repeat contributors, response/review time | Exclude maintainer and bot activity from community-growth claims. |
| Advocacy | Organic stars, forks, mentions, dependent repositories, return visitors | Treat stars as a lagging outcome, not an acceptance criterion for engineering work. |

Suggested launch gates, not promised growth targets:

- Gate 1: all advertised installation paths work from public artifacts.
- Gate 2: the supported compatibility matrix is green and visible.
- Gate 3: community/security/release files and repository settings are complete.
- Gate 4: three high-value, tested recipes have visual or inspectable proof.
- Gate 5: at least one external user completes the five-minute flow without maintainer intervention; record friction and revise onboarding.

## Explicit non-goals

- Do not promise a number of GitHub stars or describe the project as viral before independent usage exists.
- Do not add dozens of commands before fixing publication, compatibility proof, and contributor entry points.
- Do not ship standalone binaries yet unless demand justifies signing, multi-platform build, FFmpeg licensing/distribution, startup-size, and update work. The current wheel/sdist decision is sensible.
- Do not silently bundle or auto-download FFmpeg without a separate licensing, integrity, and update design.
- Do not collect opt-out CLI telemetry to manufacture usage data. Prefer public repository/package metrics and opt-in user research.
- Do not claim “secure” because badges are green. Publish the exact controls and unresolved limitations.
- Do not chase an OpenSSF score mechanically. Prioritize real controls, then use Scorecard as visible regression detection.
- Do not enable Discussions, a public roadmap, or response-time promises unless the maintainer can sustain them.

## Most important synthesis point

The repository already has enough implementation breadth to launch a credible beta. The highest-leverage sequence is:

1. repair the false install promise by publishing an attested release;
2. make support claims match tested Python/OS/FFmpeg reality;
3. complete security and contribution entry points;
4. turn the README into a short proof-led activation path;
5. establish repeatable release, recipe, and contributor loops;
6. only then expand commands based on observed user demand.

This sequence will not guarantee stars. It removes the concrete reasons that a qualified visitor currently cannot install, trust, recommend, or contribute to PyFFmpegCore.
