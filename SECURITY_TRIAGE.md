# Security alert triage

Updated: 24 September 2026. This is an evidence log, not a claim that every
open alert is exploitable or that the project has no vulnerabilities. The
container evidence below remains from 19 September; no newer image scan was run.

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

The [Trixie candidate run](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35449281881)
also built and smoke-tested both architectures without publishing them. Its
complete amd64 and arm64 reports each contain 592 findings (1 CRITICAL, 206
HIGH, 203 MEDIUM, 164 LOW, and 18 UNKNOWN across 215 rule IDs), while both
blocking reports contain zero HIGH/CRITICAL findings with a known fixed
version. The candidate artifacts identify Debian 13.7 and image IDs
`sha256:5acf802a5256b4fbdd55709545e22970b3d2dea5364560f68bb1b43c4f6be2f6`
(amd64) and
`sha256:945e00ad92bdb7f0dcf8949109e2a540aeba0f17195804e9bd0f5b25e0987496`
(arm64). They are scan evidence only; the public GHCR digest above remains the
one documented for users until a separately authorized publication.

## GitHub alert inventory

At the historical 19 September 2026 snapshot after `b9ceea7`, GitHub Code
Scanning listed **481 open Trivy alerts** and **1 open Scorecard alert**. Alert
instances span repeated scans and are not the same unit as the 874 findings in
one image scan or 366 distinct Trivy rule IDs. The current Scorecard SARIF also
reports Branch Protection and Code Review scores; not every SARIF result
appears as an open alert.

The live inventory was rechecked on 23 September after `0952c0e`. It lists
**483 open Trivy alerts** (97 high, 199 medium, 164 low, 23 without a severity
level) and **1 open Scorecard alert**, the low-severity
`CIIBestPracticesID`. The Trivy alerts are instances from the scheduled
Container analysis [run 35847548151](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35847548151)
on the older commit `25adc43150842930f84e25c105a7612f1a4b02f1`; they are not a
fresh scan of the published digest. The current
[Scorecard run 35913522219](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35913522219)
passed on `0952c0ef57d13962bc4544bd300ccb0a585d47d8`; the three
`TokenPermissionsID` alerts are no longer open. Workflow defaults are
read-only, with required write scopes assigned to the relevant job. No new
container was built, scanned, or published for this update.

The paginated GitHub Code Scanning API inventory was checked again on 24
September at `259834267d2c0b1859cd02f69cdeef670e8c7bfa`. It returns 484 open
alerts: 483 Trivy alerts on `25adc43150842930f84e25c105a7612f1a4b02f1` (97
HIGH, 199 MEDIUM, 164 LOW, 23 without severity) and one LOW
`CIIBestPracticesID` Scorecard alert on `main` at the inventory SHA. CodeQL
run [`35934789805`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35934789805),
Scorecard run
[`35934789837`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35934789837),
and CI run
[`35934789814`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35934789814)
passed on that exact SHA. This read did not run a container scan.

The hash-bearing wheel install in the Action and the public terminal demo
removed the open `PinnedDependenciesID` instances. The successful
[ClusterFuzzLite run](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35449599477)
is now recognized by Scorecard, and its Fuzzing alert is closed. The remaining
Scorecard alert is the OpenSSF Best Practices badge, which requires an
authenticated external project enrollment; no badge has been awarded. A
passing Scorecard analysis job does not mean all its checks score highly.
Direct pushes to `main`, including those requested for this implementation, do
not create a reviewed PR history.

## Remediation order

1. Keep the weekly complete scan and fail on fixable HIGH/CRITICAL findings.
   When a fixed Debian version appears, refresh the pinned base and installed
   packages, publish a new digest, and recheck both architectures.
2. Maintain the hash-bearing CI/release dependency locks across the supported
   Python/OS matrix and recheck wheel and sdist installs after updates.
3. Maintain the bounded pipeline/profile/receipt parser fuzz corpus, the
   ClusterFuzzLite integration, and CI crash artifacts. Keep the recognized
   fuzzer target and its base image pinned as they evolve.
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

The [ClusterFuzzLite build](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35449599477)
now builds the Atheris parser target as the expected `parser_fuzzer.pkg` plus
wrapper and runs the configured address-sanitized fuzzing job. Scorecard's
Fuzzing alert is closed after that run.

Hash-bearing, wheel-only tool locks now cover CI, docs, release build, pipx
verification, the public terminal demo, and container build inputs. The
[current CI matrix](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35449898003),
[CodeQL run](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35449897997),
[Scorecard run](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35449898050),
[release dry run](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35445461779),
and new two-architecture container scan succeeded. Public wheel smoke
deliberately uses the normal resolver to test user installation.
