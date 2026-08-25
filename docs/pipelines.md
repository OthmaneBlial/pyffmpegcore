# Declarative pipelines

Pipelines compose maintained profiles and typed workflows as a dependency graph.
They never accept raw shell commands or arbitrary FFmpeg strings. The exact
argument arrays still pass through normal planning, preflight, execution,
progress, cleanup, and receipt contracts.

Three golden templates ship in the repository:

- [`web-publish.json`](https://github.com/OthmaneBlial/pyffmpegcore/blob/main/pipelines/web-publish.json) creates a browser-compatible video and poster.
- [`podcast-package.toml`](https://github.com/OthmaneBlial/pyffmpegcore/blob/main/pipelines/podcast-package.toml) normalizes speech and creates a waveform.
- [`video-thumbnails-subtitles.json`](https://github.com/OthmaneBlial/pyffmpegcore/blob/main/pipelines/video-thumbnails-subtitles.json) adds captions, makes a web copy, and creates a poster.

Every template runs against generated real media in CI.

## Validate, visualize, and preview

```bash
pyffmpegcore pipeline validate pipelines/web-publish.json --json
pyffmpegcore pipeline graph pipelines/web-publish.json --format mermaid
pyffmpegcore pipeline run pipelines/web-publish.json --explain --plan-json
```

Whole-pipeline preflight checks the dependency graph, external inputs,
capabilities, output parents, collisions, and disk space before mutation.
Inputs produced by an earlier step are reported as explicitly deferred rather
than incorrectly treated as existing files.

The dependency graph can be rendered as compact text, Mermaid, or Graphviz DOT.
References use an exact typed form:

```json
{
  "id": "poster",
  "workflow": "thumbnail",
  "input": "${steps.web_video.output}",
  "output": "${OUTPUT_DIR}/poster.jpg",
  "options": {"timestamp": "00:00:00.100", "width": 1280}
}
```

The reference automatically creates a dependency. Explicit `needs` can add
ordering constraints when no output is consumed.

## Run, cancel, and resume

```bash
pyffmpegcore pipeline run pipeline.json \
  --state .pyffmpegcore/pipeline-state.json \
  --events .pyffmpegcore/pipeline-events.jsonl \
  --receipt-dir .pyffmpegcore/receipts \
  --result-json

pyffmpegcore pipeline run pipeline.json \
  --state .pyffmpegcore/pipeline-state.json \
  --resume \
  --result-json
```

A failed step blocks only its dependants. Independent later steps can still
run, and the result keeps deterministic topological order. `Ctrl-C` sets the
same cancellation contract used by one-off workflows. State is written
atomically after each successful step and contains only step IDs and cache
keys—never source paths or secret values.

## Optional content-aware cache

```json
{
  "cache": {
    "enabled": true,
    "directory": ".pyffmpegcore/cache",
    "content_aware": true
  }
}
```

This is a completion cache, not a hidden artifact store. A step is skipped only
when its redacted typed plan, input fingerprint, saved key, and every expected
output match. With `content_aware: true`, local inputs use SHA-256; otherwise the
fingerprint uses size and modification time. Deleted outputs or changed inputs
run again.

## Keep secrets outside files

Declare only the variable name:

```json
{
  "secret_variables": ["SOURCE_URL"]
}
```

Then provide its value through the environment without putting it in the
pipeline or command line:

```bash
export SOURCE_URL='https://user:token@example.test/private/video.mp4'
pyffmpegcore pipeline run private.json --var SOURCE_URL --receipt-dir receipts
```

Secret defaults in pipeline files are rejected. Named values are masked from
plans, JSON output, event logs, cache keys, and per-step receipts. URL userinfo
and query strings also use the normal receipt redaction policy.

## Schema migration

```bash
pyffmpegcore pipeline migrate old.toml pipeline-1.0.json --to 1.0
```

Migration validates and writes canonical JSON. A source or target version with
no explicit migration path fails rather than guessing. See the
[pipeline JSON schema](schemas/pipeline-1.0.schema.json).
