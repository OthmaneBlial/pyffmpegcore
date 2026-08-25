# Dry runs and deterministic plans

Every command that can write media accepts `--dry-run` and `--explain`. Both modes are non-mutating: they do not create output directories, temporary files, pass logs, or media outputs.

```bash
pyffmpegcore convert \
  --input input.webm \
  --output output.mp4 \
  --video-codec libx264 \
  --audio-codec aac \
  --explain
```

`--dry-run` shows the exact argument vector, overwrite policy, expected outputs, and preflight. `--explain` also spells out selected/copied/dropped streams, codecs, filters, quality or size trade-offs, and hardware policy.

Use `--plan-json` with either preview mode for automation:

```bash
pyffmpegcore compress \
  --input talk.mov \
  --output upload.mp4 \
  --target-size 25MB \
  --min-video-bitrate 150k \
  --dry-run \
  --plan-json > plan.json
```

The `command` and each multi-pass `steps[].command` value are JSON arrays, never shell strings. Human output uses unambiguous shell-like quoting only for display; PyFFmpegCore executes the original array without a shell.

Plans normalize paths so the same request is snapshot-testable. Environment-specific capability and free-space facts live in the separate preflight object and do not change the plan.

## Execute and keep a machine result

Every writing command compiles through the same planner, preflight engine, and executor as its preview. Add `--result-json` to execute the job and emit one parseable document containing the exact plan, preflight checks, per-item `JobResult`, and success/failure counts:

```bash
pyffmpegcore thumbnail \
  --input talk.mov \
  --output poster.jpg \
  --result-json > result.json
```

Progress and human summaries are suppressed in this mode so stdout remains valid JSON. The normal stable exit categories still apply: `0` success, `3` environment, `4` validation/preflight, `5` execution, and `6` partial batch success. `--result-json` executes media and therefore cannot be combined with the non-mutating `--dry-run` or `--explain` modes.

## Execute the same plan from Python

`WorkflowEngine` exposes the same planner, preflight, item-aware execution, and stable result envelope used by the CLI:

```python
from pyffmpegcore import WorkflowEngine

engine = WorkflowEngine()
plan = engine.planner.thumbnail("talk.mov", "poster.jpg", timestamp="00:00:03")
batch = engine.run(plan)

if batch.succeeded:
    print(batch.items[0].result.outputs)
else:
    print(batch.items[0].result.stderr)
```

The engine executes the exact typed plan and returns a `WorkflowBatch` containing item-level `JobResult` values rather than exposing only a raw process object. FFmpeg's `-progress pipe:1` protocol is part of every workflow plan, and the final normalized `ProgressEvent` is stored in the result. A callback can receive the typed events while the job runs.

The execution policy controls overwrite refusal, timeout, cancellation, captured output, and temporary-file retention. CLI jobs expose `--timeout SECONDS` and `--temp-files clean|keep-on-error|keep`; `Ctrl-C` terminates the active FFmpeg child and records a cancelled result. Two-pass logs, concat manifests, and defensive subtitle copies are materialized in an isolated workspace only when execution begins. The default `clean` policy removes that workspace after success or failure; retention is always explicit.

## Target-size feasibility

`--target-size` accepts explicit decimal (`MB`, `GB`) or binary (`MiB`, `GiB`) units. The plan reserves audio and container overhead, calculates the two-pass video bitrate, and enforces `--min-video-bitrate`. An impossible target fails before FFmpeg starts and states the minimum feasible byte count.

`--target-size-kb` remains available for compatibility but is less clear than an explicit unit.
