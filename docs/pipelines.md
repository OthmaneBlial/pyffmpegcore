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
keys—never source paths or secret values. A fresh explicit state path is
claimed exclusively before the first runnable step; a concurrent default run
fails rather than replacing it.

### PowerShell: variable, evidence, and resume

From a repository checkout with PyFFmpegCore and FFmpeg installed, generate
the local fixture and run the included `web-publish.json` template. The
template declares `INPUT` and `OUTPUT_DIR`; `--var` passes only their names
and reads their values from the environment. Quoted paths keep spaces intact.

```powershell
python tests/media/download_fixtures.py --force
New-Item -ItemType Directory -Force "build" | Out-Null
$env:INPUT = (Resolve-Path "tests/media/downloads/sample_video_mov.mov").Path
$env:OUTPUT_DIR = Join-Path (Get-Location).Path "build/Web Publish"

pyffmpegcore pipeline run "pipelines/web-publish.json" `
  --var INPUT --var OUTPUT_DIR `
  --receipt-dir "build/Pipeline Receipts" `
  --events "build/Pipeline Events.jsonl" `
  --state "build/Pipeline State.json" `
  --result-json

pyffmpegcore pipeline run "pipelines/web-publish.json" `
  --var INPUT --var OUTPUT_DIR `
  --receipt-dir "build/Pipeline Receipts" `
  --events "build/Pipeline Events.jsonl" `
  --state "build/Pipeline State.json" `
  --resume --result-json
```

The first run writes one redacted receipt per step, JSON Lines events, and
atomic resume state. The second run reuses steps only when their signatures
and outputs still match; inspect the result's item statuses. Receipts omit
private paths by default. Existing receipts are preserved unless `--force` or
`--resume` is used; the Python API accepts `overwrite_receipts=True`. Receipt
destinations that collide with media outputs are rejected before steps start.
State destinations that collide with media outputs or receipts are rejected
before execution, including through the Python API. Existing explicit state
files are preserved unless `--force`, `--resume`, or `overwrite_state=True` is
used. The pipeline's own cache state remains reusable by default.
State, event log, per-step receipts, and media outputs must use distinct
paths; the CLI rejects collisions before opening the event log.
Do not put credentials in the command, pipeline file, or `OUTPUT_DIR` value.

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
plans, result JSON, cache keys, and per-step receipts. When a declared secret is
active, CLI event logs omit event details because FFmpeg diagnostics can echo a
source URL. URL userinfo and query strings also use the normal receipt
redaction policy in other artifacts.

Remote inputs require a server that supports the access pattern of the media.
In a local replay on 19 September 2026, a fast-start MP4 completed over HTTP,
while a MOV whose `moov` atom followed `mdat` failed against a minimal server
without byte-range seeking. Use a server with working ranges or download the
file locally first. FFmpeg documents [HTTP seekability](https://ffmpeg.org/ffmpeg-protocols.html#http)
and [the `faststart` layout](https://ffmpeg.org/ffmpeg-formats.html#mov_002c-mp4_002c-ismv).
The Action needs `network: bridge` for an intentional remote input.

## Schema migration

```bash
pyffmpegcore pipeline migrate old.toml pipeline-1.0.json --to 1.0
```

Migration validates and writes canonical JSON. A source or target version with
no explicit migration path fails rather than guessing. See the
[pipeline JSON schema](schemas/pipeline-1.0.schema.json).
