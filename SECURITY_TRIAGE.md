# Security alert triage

Snapshot: 19 September 2026. This is an evidence log, not a claim that every
open alert is exploitable or that the project has no vulnerabilities.

## Current container evidence

The [successful container run](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35446437477)
built and published
`ghcr.io/othmaneblial/pyffmpegcore@sha256:796661ae57874f07221e9ad258499b9a9473282544744615c7b40b719aadbc9a`.
Its `container-evidence-35446437477` artifact contains separate complete Trivy
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

At the 19 September 2026 snapshot after `3a7315d`, GitHub Code Scanning lists
**697 open Trivy alerts** and **4 open Scorecard alerts**. Alert instances span
repeated scans and are not the same unit as the 874 findings in one current
image or 366 distinct Trivy rule IDs. The current Scorecard SARIF also reports Branch Protection and Code
Review scores; not every SARIF result appears as an open alert.

The lock reduced open `PinnedDependenciesID` instances from 19 to **2**. One
points at a `pip install --no-index --no-deps --no-build-isolation .` command
for the source already checked out at a commit SHA; this command fetches no
external package. The other points at the real public `pip install
pyffmpegcore==...` shown by the terminal demo, which intentionally exercises
ordinary user installation. These are recorded as scanner limitations for
their specific purpose, not dismissed alerts. The other two open alerts are
Fuzzing and the OpenSSF Best Practices badge. The earlier CI Tests and SAST
alerts are no longer open after recent CI and CodeQL runs; this is an
observation of GitHub's current inventory, not a claim about future commits.
The bounded parser fuzzer has not satisfied Scorecard's recognized
external-fuzzer criterion. No Best Practices badge has been awarded. A passing
Scorecard analysis job does not mean all its checks score highly. Direct
pushes to `main`, including those requested for this implementation, do not
create a reviewed PR history.

## Remediation order

1. Keep the weekly complete scan and fail on fixable HIGH/CRITICAL findings.
   When a fixed Debian version appears, refresh the pinned base and installed
   packages, publish a new digest, and recheck both architectures.
2. Maintain the hash-bearing CI/release dependency locks across the supported
   Python/OS matrix and recheck wheel and sdist installs after updates.
3. Maintain the bounded pipeline/profile/receipt parser fuzz corpus and CI
   crash artifacts. Evaluate a recognized continuous-fuzzing integration if
   the corpus and maintenance cost justify it.
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
The [successful CI run on `75790c6`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35445459849)
executed three parser targets with 1,003 cases per target and two seeds, and
provides a crash artifact when a job fails. This is parser-only fuzzing; it
does not exercise FFmpeg on hostile media or prove every possible input safe.

Hash-bearing, wheel-only tool locks now cover CI, docs, release build, pipx
verification, and container build inputs. The
[three-OS CI matrix](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35445459849),
[release dry run](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35445461779),
and new two-architecture container scan succeeded. Public wheel smoke
deliberately uses the normal resolver to test user installation.
