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

The `command` and each multi-pass `steps[].command` value are JSON arrays, never shell strings. Human output uses platform-appropriate quoting only for display; PyFFmpegCore executes the original array without a shell.

Plans normalize paths so the same request is snapshot-testable. Environment-specific capability and free-space facts live in the separate preflight object and do not change the plan.

## Target-size feasibility

`--target-size` accepts explicit decimal (`MB`, `GB`) or binary (`MiB`, `GiB`) units. The plan reserves audio and container overhead, calculates the two-pass video bitrate, and enforces `--min-video-bitrate`. An impossible target fails before FFmpeg starts and states the minimum feasible byte count.

`--target-size-kb` remains available for compatibility but is less clear than an explicit unit.
