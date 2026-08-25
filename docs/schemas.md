# JSON schemas

Machine-readable outputs are versioned as their contracts stabilize.

## `doctor --json`

The current beta document contains `cli_version`, `platform`, `python`, `ffmpeg`, `ffprobe`, and `capabilities`. The versioned capability inventory includes full encoder, decoder, filter, muxer, demuxer, protocol, subtitle, and hardware-accelerator facts plus core availability summaries.

## `probe --json`

The simplified probe document contains format fields, normalized duration/size/bitrate, tags, stream summaries, dispositions, language, rotation, color/HDR facts, side data, attachments, and chapters. Python callers can request `raw=True` or call `probe_raw()` for the lossless FFprobe document.

## `smoke-test --json`

The document uses `schema_version: "1.0"` and reports status, retention behavior, workspace policy, and probe summaries for the synthetic input and generated thumbnail.

## Plans, results, profiles, and preflight

- `ExecutionPlan` uses `schema_version: "1.0"` and stores the exact argument vector as an array.
- `JobResult` uses `schema_version: "1.0"` and categorizes success, runtime failure, timeout, cancellation, and validation refusal. It includes the final normalized `ProgressEvent`, capture-policy output, warnings, and output existence/size facts.
- profiles use `schema_version: "1.0"` plus an independent positive `profile_version`.
- `PreflightReport` uses `schema_version: "1.0"`; human output is rendered from the same check objects.
- `WorkflowBatch` uses `schema_version: "1.0"` and is the shared CLI/Python envelope around a prepared plan and ordered item executions.
- Batch manifests, state files, JSONL events, and ordered outcomes use independent `1.0` contracts. See the [batch manifest schema](schemas/batch-manifest-1.0.schema.json), [example](schemas/batch-manifest-1.0.example.json), and [batch guide](batches.md).

Writing commands accept `--result-json`. Its version `1.0` envelope contains `plan`, `preflight`, ordered `items`, and a `summary`. Each item records its input/output identity, item-specific preflight, and stable `JobResult`. Batch image jobs therefore retain the same schema for total success, total failure, and partial success.

Run receipts use their own [`1.0` JSON Schema](schemas/run-receipt-1.0.schema.json),
[redacted example](schemas/run-receipt-1.0.example.json), and explicit
[privacy/migration contract](receipts.md). Human terminal output is allowed to
evolve; versioned JSON fields follow the documented compatibility and
deprecation policy.
