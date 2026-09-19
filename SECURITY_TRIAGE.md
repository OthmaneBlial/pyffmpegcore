# Security alert triage

Snapshot: 19 September 2026. This is an evidence log, not a claim that every
open alert is exploitable or that the project has no vulnerabilities.

## Current container evidence

The [successful container run](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35443612193)
built and published
`ghcr.io/othmaneblial/pyffmpegcore@sha256:538bbee63b043ac9a3716230c1859766dfe617070f85b5900089eb18a1fae019`.
Its `container-evidence-35443612193` artifact contains separate complete Trivy
SARIF and blocking reports for amd64 and arm64 candidates. Each blocking report
has **zero** HIGH/CRITICAL findings with a known fixed version. The complete
amd64 report has **874 package findings** across **366 rule IDs**: 11 CRITICAL,
241 HIGH, 363 MEDIUM, 226 LOW, and 33 UNKNOWN. The arm64 report has **863
findings** across **356 rule IDs**. Every finding in both reports has an empty
`Fixed Version` field. The scan gate passing therefore does not mean that the
image is vulnerability-free. Both candidates also passed non-root runtime,
`doctor`, and synthetic smoke checks; arm64 ran under QEMU. The published OCI
index and its two platform manifests were fetched anonymously, and the digest
passed `gh attestation verify`.

The six previously fixable PCRE2 advisories in the earlier image are no longer
open after the base refresh and Debian package upgrade. Two new open instances
of `CVE-2026-8674` affect `libc-bin` and `libc6`; Trivy currently reports no
fixed version for either. Do not dismiss them solely to reduce the alert count.

## GitHub alert inventory

At the `a44a64d` snapshot, GitHub Code Scanning lists **697 open Trivy alerts**
and **6 open Scorecard alerts**. Alert instances span repeated scans and are not
the same unit as the 874 findings in one current image or 366 distinct Trivy
rule IDs. The current Scorecard SARIF also reports Branch Protection and Code
Review scores; not every SARIF result appears as an open alert.

The lock reduced open `PinnedDependenciesID` instances from 19 to **2**. One
points at a `pip install --no-index --no-deps --no-build-isolation .` command
for the source already checked out at a commit SHA; this command fetches no
external package. The other points at the real public `pip install
pyffmpegcore==...` shown by the terminal demo, which intentionally exercises
ordinary user installation. These are recorded as scanner limitations for
their specific purpose, not dismissed alerts. The other four are CI Tests,
SAST coverage, Fuzzing, and the OpenSSF Best Practices badge. The CI Tests
message reports tests on one of three sampled merged PRs; SAST reports a scan
on one of three sampled commits, despite current CodeQL runs succeeding on
`main`. The new bounded parser fuzzer may not satisfy Scorecard's recognized
external-fuzzer criterion. No Best Practices badge has been awarded. The
Scorecard run passes as an analysis job, not as a remediation gate. Direct pushes to `main`, including those
requested for this implementation, do not create the reviewed PR history that
the CI Tests and Code Review checks reward.

## Remediation order

1. Keep the weekly complete scan and fail on fixable HIGH/CRITICAL findings.
   When a fixed Debian version appears, refresh the pinned base and installed
   packages, publish a new digest, and recheck both architectures.
2. Replace unbounded `pip install` commands in CI and release tooling with a
   reviewed, hash-bearing dependency lock that covers the supported Python/OS
   matrix. Verify wheel and sdist installs from those exact inputs.
3. Add reproducible fuzzing for the pipeline/profile/receipt parsers and their
   validation boundaries. Run it under CI with bounded time and preserved crash
   artifacts, then seek continuous fuzzing integration if the corpus justifies it.
4. Check that CodeQL and required tests finish on the same proposed revision.
   A maintainer should decide the repository's review policy before changing
   branch protection or claiming that Scorecard's PR-history findings are fixed.
5. Work through the OpenSSF Best Practices criteria with public evidence. Do
   not claim a badge until the external project record grants it.

No alerts were bulk dismissed as part of this triage. Scan evidence and
remaining findings should be reevaluated for each published digest.

## Application-level URL handling

An audit reproduction found that a media URL could be normalized into a local
path, exposing a dummy credential in a single-command `--explain` output. A
local HTTP pipeline replay also showed FFmpeg echoing its input URL inside the
`--result-json` stderr field even though the receipt masked it. Commit
`16371ec` preserves remote URIs in pipeline plans, rejects direct CLI URL
paths without echoing them, and redacts URLs embedded in published diagnostics.
The new real-media test serves a fixture over loopback HTTP with a dummy
credential and checks both the JSON result and receipt. It does not claim a
general sandbox or guarantee redaction of every future third-party message.

## Parser fuzzing and dependency locks

The September 19 parser corpus uses bounded byte and structure mutations for
pipeline, profile, and receipt files. It found an invalid UTF-8 receipt that
raised `UnicodeDecodeError` outside the public validation boundary;
`RunReceipt.read` now raises `ValidationError`, with a focused regression.
The CI fuzz job and its crash artifact are pending a successful run on the
fixing SHA. This is parser-only fuzzing; it does not exercise FFmpeg on hostile
media or prove every possible input safe.

Hash-bearing, wheel-only tool locks now cover CI, docs, release build, pipx
verification, and container build inputs. A macOS/Python 3.14 clean install,
local build, archive checks, and fast tests passed. The three-OS matrix,
release dry run, and updated container scan are still being checked. Public
wheel smoke deliberately uses the normal resolver to test user installation.
