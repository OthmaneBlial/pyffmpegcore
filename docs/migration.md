# Migration notes

## From 0.1.x source checkouts to 0.2.x

- Python 3.10 is now the minimum supported interpreter.
- Global CLI options behave consistently before or after subcommands.
- Incomplete grouped commands return usage code `2` instead of success.
- `--verbose` emits selected command and binary diagnostics.
- The package version is sourced from `pyffmpegcore.__version__`.
- Test fixtures are generated locally and the old mutable download assumptions no longer apply.
- The public release contract adds exact-artifact tests, stable quality gates, and security/release policies.
- CLI handlers and repository examples now use `WorkflowEngine`; experimental examples that assembled raw FFmpeg arrays were removed from the supported examples.

Prefer the shared engine in Python:

```python
from pyffmpegcore import WorkflowEngine

engine = WorkflowEngine()
batch = engine.run(engine.planner.extract_audio("video.mp4", "audio.mp3"))
result = batch.items[0].result
```

`FFmpegRunner` convenience methods now compile typed shared plans and return `JobResult`. They no longer accept arbitrary `**kwargs`; the renamed explicit parameters are `pixel_format`, `container_overhead_percent`, and `minimum_video_bitrate`. New code should prefer `WorkflowEngine` when it needs the plan, preflight, and item envelope together.

The low-level `FFmpegRunner.run(args)` escape hatch still returns `CompletedProcess`, never invokes a shell, and injects overwrite refusal (`-n`) unless the argument vector already contains an explicit `-n` or `-y`.

The Python API remains beta. Public incompatible changes require a changelog entry, migration example, and deprecation window when security and correctness allow.
