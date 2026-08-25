# PyFFmpegCore

**Preflight the media stack. Preview the exact FFmpeg plan. Run a maintained
workflow. Keep a privacy-redacted receipt.**

PyFFmpegCore is a safe, explainable FFmpeg task runner for developers and
technical creators automating local or CI media jobs. It supports Python
3.10–3.14 on Linux, macOS, and Windows and requires external `ffmpeg` and
`ffprobe` executables. It does not bundle codecs, replace arbitrary FFmpeg
filter graphs, expose packet/frame internals, or provide hosted transcoding.

[![CI](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/ci.yml/badge.svg)](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/ci.yml)
[![Action integration](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/action-integration.yml/badge.svg)](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/action-integration.yml)
[![CodeQL](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/codeql.yml/badge.svg)](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/OthmaneBlial/pyffmpegcore/badge)](https://securityscorecards.dev/viewer/?uri=github.com/OthmaneBlial/pyffmpegcore)
[![License: MIT](https://img.shields.io/github/license/OthmaneBlial/pyffmpegcore)](LICENSE)

[Documentation](https://othmaneblial.github.io/pyffmpegcore/) ·
[Five-minute start](https://othmaneblial.github.io/pyffmpegcore/quickstart/) ·
[Recipes](https://othmaneblial.github.io/pyffmpegcore/recipes/) ·
[Reproducible evidence](https://othmaneblial.github.io/pyffmpegcore/evidence/) ·
[Security](SECURITY.md)

## Install and prove one useful result

Until the first PyPI release is public, install the latest validated source
revision in an isolated environment:

```bash
pipx install git+https://github.com/OthmaneBlial/pyffmpegcore.git@8c7e3a91833d7d0c4215bbe512176842588dc1fa
pyffmpegcore doctor
pyffmpegcore smoke-test
```

Turn an editor/camera MOV into a conservative web MP4. First inspect the plan
without writing anything, then execute the same profile and keep its receipt:

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

The successful command reports the output container, duration, byte size,
video/audio codecs, and receipt path. The receipt records the redacted plan,
preflight facts, tool versions, probes, elapsed result, and stable exit category:

```text
Output: web.mp4
Container: mov,mp4,m4a,3gp,3g2,mj2
Duration: 6.00 seconds
Size: 542.1 KB
Video: h264 640x360
Receipt: web.receipt.json
```

Those numbers come from the deterministic proof fixture. Your duration and size
will reflect your input.

## Current support contract

| Environment | Continuously tested claim |
| --- | --- |
| Python | 3.10–3.14 package contract on Linux |
| Ubuntu | Exact-wheel media smoke on Python 3.10 and 3.14 |
| macOS | Exact-wheel media smoke on Python 3.10 and 3.14 |
| Windows | Exact-wheel media smoke on Python 3.10 and 3.14 |
| FFmpeg | Current runner packages; exact versions captured in CI evidence |

The [compatibility policy](docs/COMPATIBILITY.md) distinguishes tested cells
from combinations expected to work. A workflow can still reject a missing
encoder, filter, muxer, protocol, stream, writable destination, or disk-space
requirement before mutation.

## Why this instead of another wrapper?

Raw FFmpeg remains the right choice when you already own and review the full
argument vector. Graph builders are better for arbitrary filter graphs; PyAV is
better for packet/frame access; array-oriented libraries are better for NumPy
or image-processing loops.

PyFFmpegCore is for a different job:

```text
diagnose -> preflight -> deterministic plan -> typed workflow -> result -> receipt
```

- no shell interpolation of paths or untrusted values;
- explicit overwrite, timeout, cancellation, cleanup, and exit-code policies;
- maintained profiles with capability-aware failure and fallback guidance;
- human explanations and versioned machine output from the same plan;
- deterministic media fixtures and real FFmpeg execution in CI;
- no default telemetry and no content hashing unless requested.

See the [factual comparison](docs/comparison.md) with raw FFmpeg,
`ffmpeg-python`, `python-ffmpeg`, `ffmpegio`, and PyAV.

## Measured proof, not decorative screenshots

These three jobs ran on 2026-08-25 against generated, first-party fixtures:

| Workflow | Before | After |
| --- | ---: | ---: |
| Web-compatible video | 688,662-byte MOV | 555,083-byte H.264 MP4; 19.4% smaller |
| Fit under 256 KiB | 4,042,503-byte MP4 | 248,417 bytes; target passed |
| Podcast loudness | -22.0 LUFS WAV | -16.2 LUFS MP3 for a -16.0 LUFS target |

Review the [full commands, probe facts, redacted receipts, and receipt
checksums](docs/evidence.md). The [real-media methodology](docs/test-methodology.md)
explains fixture generation, capability skips, failure contracts, and artifact
validation.

## Three high-value recipes

### Make a portable web video

```bash
pyffmpegcore profile run web/mp4-compatible \
  --input source.mov --output web.mp4 --receipt web.receipt.json
```

[Input contract and verification](docs/recipes/web-video.md)

### Fit an upload under a byte limit

```bash
pyffmpegcore compress \
  --input upload.mp4 --output upload-small.mp4 \
  --target-size 24MiB --two-pass --receipt upload.receipt.json
```

[Feasibility, quality floor, and measured proof](docs/recipes/exact-size.md)

### Normalize spoken-word audio

```bash
pyffmpegcore normalize-audio \
  --input episode.wav --output episode.mp3 \
  --method loudnorm --receipt episode.receipt.json
```

[Loudness targets and listening checks](docs/recipes/podcast.md)

The complete command catalog is generated into the [CLI
reference](https://othmaneblial.github.io/pyffmpegcore/reference/cli/). More
task-first recipes cover subtitles, thumbnails, audio extraction, and image
batches.

## Repeatable automation

Compose existing typed workflows in strict JSON or TOML—never raw shell
strings—then validate, visualize, dry-run, execute, resume, or cache the DAG:

```bash
pyffmpegcore pipeline validate pipelines/web-publish.json
pyffmpegcore pipeline graph pipelines/web-publish.json --format mermaid
pyffmpegcore pipeline run pipelines/web-publish.json \
  --receipt-dir receipts --state pipeline-state.json --events events.jsonl
```

CI can use the [digest-pinned GitHub Action](docs/github-action.md). Container
users can pull the public `linux/amd64` and `linux/arm64` image by the verified
digest documented in the [container guide](docs/container.md); its workflow
blocks fixed high/critical vulnerabilities and publishes SBOM, provenance, and
Sigstore attestation evidence.

## Python API

The CLI and Python layer use the same typed planner and workflow engine:

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

Public types, exceptions, and stability rules are in the [Python API
reference](https://othmaneblial.github.io/pyffmpegcore/reference/python-api/).

## Trust, limits, and participation

- [Current CI and exact-artifact evidence](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/ci.yml)
- [Compatibility matrix](docs/COMPATIBILITY.md)
- [Security policy and private reporting](SECURITY.md)
- [Command-execution threat model](docs/SECURITY_MODEL.md)
- [Release, provenance, and recovery procedure](docs/RELEASING.md)
- [Contribution ladder and test tiers](CONTRIBUTING.md)
- [Support and triage expectations](SUPPORT.md)
- [Changelog](CHANGELOG.md)

The project is pre-PyPI until Trusted Publishing succeeds. Source installation
is useful for evaluation, but it is not a released artifact. No PyPI badge,
download claim, or immutable release claim is shown before the public endpoints
work.
