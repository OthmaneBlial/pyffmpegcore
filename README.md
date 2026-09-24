<p align="center">
  <img src="https://raw.githubusercontent.com/OthmaneBlial/pyffmpegcore/main/docs/assets/pyffmpegcore-hero.svg" alt="PyFFmpegCore: preflight, plan, run, and receipt" width="100%">
</p>

# PyFFmpegCore

<p align="center">
  <strong>The safe, explainable FFmpeg task runner for the terminal, Python, and CI.</strong><br>
  Make jobs reviewable before they run and verifiable after.
</p>

<p align="center">
  <a href="https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="https://pypi.org/project/pyffmpegcore/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/pyffmpegcore"></a>
  <a href="https://www.npmjs.com/package/@othmaneblial/pyffmpegcore"><img alt="npm version" src="https://img.shields.io/npm/v/%40othmaneblial%2Fpyffmpegcore"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/github/license/OthmaneBlial/pyffmpegcore"></a>
</p>

<p align="center">
  <a href="https://othmaneblial.github.io/pyffmpegcore/">Documentation</a> ·
  <a href="docs/quickstart.md">Five-minute start</a> ·
  <a href="docs/evidence.md">Measured results</a> ·
  <a href="https://github.com/OthmaneBlial/pyffmpegcore/releases">Releases</a> ·
  <a href="https://github.com/OthmaneBlial/pyffmpegcore">⭐ Star on GitHub</a>
</p>

PyFFmpegCore turns recurring FFmpeg commands into typed workflows with a
capability check, a previewable argument plan, explicit execution policy, and a
redacted receipt. Your media stays local. FFmpeg and FFprobe remain system
dependencies.

## Install and prove one useful result

Requires Python 3.10–3.14 and `ffmpeg`/`ffprobe` on `PATH`.

```bash
pipx install "pyffmpegcore==0.3.2"
pyffmpegcore doctor
pyffmpegcore smoke-test
```

`doctor` reports the installed FFmpeg build and capabilities. `smoke-test`
creates and verifies a small synthetic clip. See the [installation guide](docs/installation.md)
for other package managers and operating systems.

Node.js users can install the [npm launcher](https://www.npmjs.com/package/@othmaneblial/pyffmpegcore); Python and FFmpeg remain required.

## Preview before writing

For example, inspect a web-compatible MP4 plan before creating the output:

```bash
pyffmpegcore profile run web/mp4-compatible \
  --input camera.mov \
  --output web.mp4 \
  --explain
```

When the plan looks right, execute it and save a machine-readable receipt:

```bash
pyffmpegcore profile run web/mp4-compatible \
  --input camera.mov \
  --output web.mp4 \
  --receipt web.receipt.json

pyffmpegcore probe --input web.mp4 --json
pyffmpegcore receipt validate web.receipt.json --json
```

Preflight checks the required encoders, filters, streams, output location, and
disk space before mutation. Results include probed output facts and stable
status categories. Overwrite refusal, timeout, cancellation, and temporary-file
cleanup are explicit policies.

## What it is good at

- Converting to maintained web, podcast, subtitle, and accessibility profiles.
- Fitting an upload limit with target-size estimates and a minimum quality floor.
- Preserving all media streams during a remux when explicitly requested.
- Running image or mixed-media batches with receipts, retries, and resume.
- Composing validated JSON or TOML media pipelines for repeatable automation.
- Explaining missing FFmpeg capabilities before a job writes files.

The [task recipes](docs/recipes/index.md) give concrete commands and limits for
each workflow. The [pipeline guide](docs/pipelines.md) covers validation,
visualization, resume, caching, and cancellation.

## Python API

The Python API uses the same planner, preflight checks, and result types as the
CLI:

```python
import threading
from pyffmpegcore import JobStatus, WorkflowEngine

engine = WorkflowEngine()
plan = engine.planner.thumbnail("talk.mov", "poster.jpg", timestamp="00:00:03")
cancellation = threading.Event()
batch = engine.run(plan, cancellation=cancellation)

# A UI cancel callback or watchdog can call cancellation.set() from another thread.
item = batch.items[0]
if item.result.status is JobStatus.CANCELLED:
    print(item.result.stderr)
```

`WorkflowEngine.run` is synchronous. Put it on a worker thread in a responsive
application, then set the shared event to stop an active FFmpeg process. See
the [Python API reference](docs/reference/python-api.md).

## Real measurements

Evidence uses reproducible inputs and publishes the commands, probes, receipts,
checksums, and limitations. For example, a public-domain Xiph VP9 clip reached
**1,035,870 bytes under a 1 MiB target** with a 7% overhead reserve; the default
5% reserve missed by 7,803 bytes. A separate compatibility conversion made an
H.264/AAC output **78.2% larger** than its VP9 input. The profile favors broader
playback compatibility; smaller output is not guaranteed.

- [Exact-size public-domain run](docs/evidence.md#public-domain-exact-size-check-on-24-september-2026)
- [Web compatibility replay](docs/evidence.md#replay-on-19-september-2026)
- [Validated 63.3-second public 0.3.2 recording](docs/terminal-demo.md)
- [Node.js launcher on npm](https://www.npmjs.com/package/@othmaneblial/pyffmpegcore)
- [Compatibility matrix and its limits](docs/COMPATIBILITY.md)

## Automation and boundaries

Pipelines use typed workflows and never accept arbitrary shell strings. CI can
use the [digest-pinned GitHub Action](docs/github-action.md). The separately
maintained container channel is documented in the [container guide](docs/container.md).

PyFFmpegCore does not download or bundle FFmpeg, provide arbitrary filter-graph
or frame APIs, run hosted transcoding, or sandbox hostile media. It does not
upload media or enable telemetry by default. Review the [security model](docs/SECURITY_MODEL.md)
before processing untrusted inputs.

## Trust and contribution

- [Signed 0.3.2 release and artifact checksums](https://github.com/OthmaneBlial/pyffmpegcore/releases/tag/v0.3.2)
- [PyPI files and provenance](https://pypi.org/project/pyffmpegcore/0.3.2/)
- [Release and recovery procedure](docs/RELEASING.md)
- [Security policy](SECURITY.md) · [Support](SUPPORT.md) · [Changelog](CHANGELOG.md)
- [Architecture](docs/architecture.md) · [Contribution guide](CONTRIBUTING.md)

If this makes a media job easier to inspect or maintain, **star the repository**.
If something fails, open an issue with the command, OS, and FFmpeg version—never
attach private media or credentials.
