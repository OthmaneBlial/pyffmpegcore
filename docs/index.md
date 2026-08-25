# Safe, explainable FFmpeg jobs

PyFFmpegCore is the safe, explainable FFmpeg task runner for the terminal, Python, and CI.

It is built for developers and technical creators who need repeatable local media jobs without maintaining raw FFmpeg command strings. Python 3.10–3.14 is supported; FFmpeg and FFprobe remain external system dependencies.

```bash
pipx install git+https://github.com/OthmaneBlial/pyffmpegcore.git@main
pyffmpegcore doctor
pyffmpegcore smoke-test
```

The source install above is the honest evaluation path until the first PyPI release is verified. PyFFmpegCore does not bundle FFmpeg, sandbox hostile media, expose every FFmpeg option, or replace a frame/packet library.

## The proof path

1. `doctor` identifies the exact binaries, builds, and important capabilities.
2. `smoke-test` generates synthetic media, transforms it, probes the output, and cleans up.
3. Task commands apply explicit overwrite and stable exit-code policies.
4. CI regenerates deterministic fixtures and exercises one immutable wheel across the support matrix.

Start with the [five-minute guide](quickstart.md), then choose a [tested recipe](recipes/index.md).

## Current trust evidence

- [CI and exact-artifact matrix](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/ci.yml)
- [Compatibility policy](COMPATIBILITY.md)
- [Deterministic media methodology](test-methodology.md)
- [Security policy](https://github.com/OthmaneBlial/pyffmpegcore/blob/main/SECURITY.md)
- [Release and recovery procedure](RELEASING.md)

## Use it when

- a known media outcome should behave consistently on a laptop and in CI;
- overwrite refusal, diagnostics, exit categories, and real-media proof matter;
- a task-focused command is more maintainable than a hand-built graph.

## Choose another tool when

- you need an arbitrary filter-graph DSL, async builder API, NumPy frame I/O, or direct packet/frame access;
- you need a hosted transcoding service or a sandbox for hostile media;
- the raw FFmpeg command is already short, well understood, and fully controlled.

See the [factual comparison](comparison.md) for the neighboring tools and their different design lanes.
