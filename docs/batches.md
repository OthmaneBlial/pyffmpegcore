# Resumable mixed-media batches

A batch manifest runs maintained profiles through the same planner, preflight,
executor, and receipt contracts used by one-off commands. Jobs can mix video,
audio, subtitle, and archival work without embedding shell strings.

```json
{
  "schema_version": "1.0",
  "policy": {
    "max_workers": 2,
    "max_retries": 1,
    "max_input_bytes": "2GiB",
    "per_job_timeout_seconds": 900
  },
  "jobs": [
    {
      "id": "web-video",
      "profile": "web/mp4-compatible",
      "input": "media/source.mov",
      "output": "build/source.mp4"
    },
    {
      "id": "podcast-audio",
      "profile": "audio/podcast-speech",
      "input": "media/episode.wav",
      "output": "build/episode.m4a"
    }
  ]
}
```

Paths are resolved relative to the manifest. Unknown fields, duplicate work,
duplicate IDs, case-insensitive output collisions, invalid profiles, and inputs
larger than the explicit resource limit fail before any job starts.

## Validate, preview, and run

```bash
pyffmpegcore batch validate batch.json --json
pyffmpegcore batch run batch.json --explain --plan-json
pyffmpegcore batch run batch.json \
  --state .pyffmpegcore/batch-state.json \
  --events .pyffmpegcore/batch-events.jsonl \
  --receipt-dir .pyffmpegcore/receipts \
  --result-json
```

`max_workers` is a hard concurrency bound from 1 to 32. `max_input_bytes` limits
each local input; it accepts an integer or a documented size such as `2GiB`.
`per_job_timeout_seconds` applies the normal cancellation and cleanup policy to
every job.

The result keeps manifest order even when jobs finish out of order. Exit code
`0` means every item succeeded, `6` means stable partial success, and the normal
environment, validation, and runtime categories apply when no item succeeds.

## Events and receipts

`--events` writes one privacy-redacted JSON object per line. Each `1.0` event
has a monotonic sequence, job ID, attempt, and one of these states:

- `queued`
- `started`
- `retrying`
- `succeeded`
- `failed`
- `cancelled`
- `resumed`

`--receipt-dir` writes one redacted run receipt for every executed item,
including deterministic failures. Content hashing remains opt-in with
`--hash-content`.

## Retry and resume safety

Retries are disabled by default. When enabled, only an explicit runtime
transport or temporarily-unavailable diagnostic is retryable. Validation,
unsupported capabilities, bad media, collisions, and missing executables are
never retried blindly.

Pass `--state FILE` on the first run to persist successful job signatures
atomically. After interruption, add `--resume`: a job is skipped only when its
ID and exact plan signature match and every expected output still exists.
Changed plans or deleted outputs run again. The state stores signatures rather
than private paths.

The complete schema and example are published under [JSON schemas](schemas.md).
