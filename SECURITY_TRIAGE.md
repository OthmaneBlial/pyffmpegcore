# Security alert triage

Snapshot: 19 September 2026. This is an evidence log, not a claim that every
open alert is exploitable or that the project has no vulnerabilities.

## Current container evidence

The [successful container run](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35441061585)
built and published
`ghcr.io/othmaneblial/pyffmpegcore@sha256:0244808caf90485eb7cf9fe99d7505b8739b90587fc8aab9ae412126e964a12c`.
Its `container-evidence-35441061585` artifact contains separate complete Trivy
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

At this snapshot, GitHub Code Scanning lists **697 open Trivy alerts** and
**23 open Scorecard alerts**. Alert instances span repeated scans and are not
the same unit as the 874 findings in one current image or 366 distinct Trivy
rule IDs. The current Scorecard SARIF also reports Branch Protection and Code
Review scores; not every SARIF result appears as an open alert.

The open Scorecard alerts comprise 19 `PinnedDependenciesID` instances from
`pip` commands without hash-pinned transitive dependencies, plus one each for
CI Tests, SAST coverage, Fuzzing, and the OpenSSF Best Practices badge. The
Scorecard run passes as an analysis job, not as a remediation gate. Direct pushes
to `main`, including those requested for this implementation, do not create the
reviewed PR history that the CI Tests and Code Review checks reward.

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
