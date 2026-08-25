<p align="center">
  <img src="https://raw.githubusercontent.com/OthmaneBlial/pyffmpegcore/main/docs/assets/pyffmpegcore-hero.svg" alt="PyFFmpegCore — preflight, plan, run, receipt" width="100%">
</p>

# PyFFmpegCore

<p align="center">
  <strong>The safe, explainable FFmpeg task runner for the terminal, Python, and CI.</strong><br>
  Diagnose the machine. Preview the exact plan. Run a maintained workflow. Keep a privacy-redacted receipt.
</p>

<p align="center">
  <a href="https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/action-integration.yml"><img alt="Action integration" src="https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/action-integration.yml/badge.svg"></a>
  <a href="https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="https://securityscorecards.dev/viewer/?uri=github.com/OthmaneBlial/pyffmpegcore"><img alt="OpenSSF Scorecard" src="https://api.securityscorecards.dev/projects/github.com/OthmaneBlial/pyffmpegcore/badge"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/github/license/OthmaneBlial/pyffmpegcore"></a>
  <a href="https://github.com/OthmaneBlial/pyffmpegcore/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/OthmaneBlial/pyffmpegcore?style=flat"></a>
</p>

<p align="center">
  <a href="https://othmaneblial.github.io/pyffmpegcore/"><strong>Explore the docs</strong></a> ·
  <a href="https://othmaneblial.github.io/pyffmpegcore/quickstart/">Five-minute proof</a> ·
  <a href="https://othmaneblial.github.io/pyffmpegcore/recipes/">Task-first recipes</a> ·
  <a href="https://othmaneblial.github.io/pyffmpegcore/evidence/">Measured evidence</a> ·
  <a href="SECURITY.md">Security</a>
</p>

PyFFmpegCore is for developers and technical creators who want repeatable
local media automation without owning a growing pile of fragile FFmpeg strings.
It supports Python 3.10–3.14 on Linux, macOS, and Windows; `ffmpeg` and
`ffprobe` remain explicit system dependencies.

```text
                  review before                    prove after
                       │                                │
input ──> preflight ──> deterministic plan ──> run ──> receipt ──> output
            │                                  │
            └─ fail before mutation            └─ timeout / cancel / cleanup
```

## Install and prove one useful result

Until the first PyPI release is public, install the latest validated source
revision in an isolated environment. The full SHA is intentional—no mutable
`main` install is presented as a release:

```bash
pipx install git+https://github.com/OthmaneBlial/pyffmpegcore.git@04d1e7051295bbcc4fa137c1214bbf340bf5c4c0
pyffmpegcore doctor
pyffmpegcore smoke-test
```

`doctor` identifies the real binaries and indexed capabilities. `smoke-test`
generates synthetic media, performs a complete transform, probes the result,
and cleans up—no checkout and no personal media required.

Now turn a camera/editor MOV into a conservative web MP4. Inspect first; write
only when the plan is acceptable:

```bash
pyffmpegcore profile run web/mp4-compatible \
  --input input.mov \
  --output web.mp4 \
  --explain

pyffmpegcore profile run web/mp4-compatible \
  --input input.mov \
  --output web.mp4 \
  --receipt web.receipt.json
```

A successful run reports output facts—not just process exit zero:

```text
Output: web.mp4
Container: mov,mp4,m4a,3gp,3g2,mj2
Duration: 6.00 seconds
Size: 542.1 KB
Video: h264 640x360
Receipt: web.receipt.json
```

Those numbers come from the deterministic proof fixture. Your duration and
size will reflect your input.

## What it owns

| PyFFmpegCore owns | It deliberately does not own |
| --- | --- |
| Capability-aware preflight before mutation | Downloading or bundling FFmpeg |
| Deterministic argument vectors and explanations | Every possible FFmpeg filter graph |
| Typed profiles, tasks, batches, and pipelines | Packet/frame internals or NumPy frame I/O |
| Overwrite, timeout, cancellation, and cleanup policy | Hosted transcoding or hostile-media sandboxing |
| Stable exit categories and redacted run receipts | Shell interpolation of paths or untrusted values |

Raw FFmpeg remains right when you already own and review the complete command.
Graph builders fit arbitrary filter graphs. PyAV fits packet/frame access.
PyFFmpegCore occupies the operational layer between intent and evidence. See
the [factual comparison](docs/comparison.md).

## Proof, not promises

These runs were made on 2026-08-25 with generated first-party fixtures. The
repository publishes the commands, input/output probes, redacted receipts, and
receipt checksums.

| Workflow | Input | Verified output |
| --- | ---: | ---: |
| Web-compatible video | 688,662-byte MOV | 555,083-byte H.264 MP4; **19.4% smaller** |
| Fit under 256 KiB | 4,042,503-byte MP4 | **248,417 bytes**; target passed |
| Podcast loudness | −22.0 LUFS WAV | **−16.2 LUFS MP3** for a −16.0 LUFS target |

[Inspect the complete evidence](docs/evidence.md) or read the [real-media test
methodology](docs/test-methodology.md), including fixture generation,
capability skips, failure contracts, and artifact validation.

## Pick an outcome

### Ship a portable web video

```bash
pyffmpegcore profile run web/mp4-compatible \
  --input source.mov --output web.mp4 --receipt web.receipt.json
```

[Input contract, plan, and verification →](docs/recipes/web-video.md)

### Hit an upload limit

```bash
pyffmpegcore compress \
  --input upload.mp4 --output upload-small.mp4 \
  --target-size 24MiB --two-pass --receipt upload.receipt.json
```

[Feasibility, quality floor, and measured proof →](docs/recipes/exact-size.md)

### Preserve every track while remuxing

```bash
pyffmpegcore convert \
  --input multilingual.mkv --output preserved.mkv \
  --preserve-all-streams --receipt preserved.receipt.json
```

[Stream-selection contract and verification →](docs/recipes/preserve-streams.md)

### Normalize spoken-word audio

```bash
pyffmpegcore normalize-audio \
  --input episode.wav --output episode.mp3 \
  --method loudnorm --receipt episode.receipt.json
```

[Loudness targets and listening checks →](docs/recipes/podcast.md)

More tested recipes cover [audio extraction](docs/recipes/audio-extraction.md),
[subtitles](docs/recipes/subtitles.md), [thumbnails](docs/recipes/thumbnails.md),
and [image batches](docs/recipes/image-batches.md). Every CLI surface is
generated into the [command reference](https://othmaneblial.github.io/pyffmpegcore/reference/cli/).

## Build repeatable media pipelines

Compose existing typed workflows in strict JSON or TOML—never raw shell
strings—then validate, visualize, dry-run, execute, resume, or cache the DAG:

```bash
pyffmpegcore pipeline validate pipelines/web-publish.json
pyffmpegcore pipeline graph pipelines/web-publish.json --format mermaid
pyffmpegcore pipeline run pipelines/web-publish.json \
  --receipt-dir receipts \
  --state pipeline-state.json \
  --events events.jsonl
```

```text
source ──> web_video ──> poster
   └─────> captions ────┘
              │
              └─ resume state + redacted receipts + JSONL progress
```

CI users can adopt the [digest-pinned GitHub Action](docs/github-action.md).
Container users get public `linux/amd64` and `linux/arm64` images with a
non-root runtime, SBOM, provenance, Sigstore attestation, and a scan that blocks
fixed high/critical vulnerabilities. The verified digest lives in the
[container guide](docs/container.md).

## Python API

The CLI and Python layer share the same typed planner, preflight, runner, and
result model:

```python
from pyffmpegcore import WorkflowEngine

engine = WorkflowEngine()
plan = engine.planner.extract_audio("video.mp4", "audio.mp3")
prepared = engine.prepare(plan)

if not prepared.preflight.ok:
    raise RuntimeError(prepared.preflight.render())

result = engine.run(plan).items[0].result
print(result.status, result.elapsed_seconds, result.outputs)
```

Public types, exceptions, and stability rules are documented in the [Python
API reference](https://othmaneblial.github.io/pyffmpegcore/reference/python-api/).

## The support contract

| Environment | Continuously tested claim |
| --- | --- |
| Python | 3.10–3.14 package contract on Linux |
| Ubuntu | Exact-wheel media smoke on Python 3.10 and 3.14 |
| macOS | Exact-wheel media smoke on Python 3.10 and 3.14 |
| Windows | Exact-wheel media smoke on Python 3.10 and 3.14 |
| FFmpeg | Current runner packages; exact versions captured in CI evidence |

The [compatibility policy](docs/COMPATIBILITY.md) separates tested cells from
combinations merely expected to work. Preflight can still reject missing
encoders, filters, muxers, protocols, streams, writable destinations, or disk
requirements before mutation.

## Trust is part of the product

- [Current CI and exact-artifact matrix](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/ci.yml)
- [Compatibility matrix](docs/COMPATIBILITY.md)
- [Security policy and private reporting](SECURITY.md)
- [Command-execution threat model](docs/SECURITY_MODEL.md)
- [Release, provenance, and recovery procedure](docs/RELEASING.md)
- [Contribution ladder and test tiers](CONTRIBUTING.md)
- [Support and triage expectations](SUPPORT.md)
- [Changelog](CHANGELOG.md)

The project is pre-PyPI until Trusted Publishing succeeds. Source installation
is useful for evaluation, but it is not a released artifact. No PyPI badge,
download claim, or immutable release claim appears before the public endpoints
and cross-platform install gate pass.

## Help make media automation less fragile

Good first contributions include a missing capability diagnostic, a real-media
fixture edge case, a task-first recipe, or a new compatibility observation.
Start with the [contribution ladder](CONTRIBUTING.md) or one of the labeled
[good first issues](https://github.com/OthmaneBlial/pyffmpegcore/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).

If PyFFmpegCore replaces one command string you no longer want to maintain,
**star the repository** so the next person searching for a safer FFmpeg layer
can find the proof.
