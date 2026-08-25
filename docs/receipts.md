# Privacy-aware run receipts

A receipt is optional evidence for one executed workflow. It records the exact
typed plan, preflight facts, tool versions, normalized progress/result facts,
warnings, and compact input/output probe summaries.

```bash
pyffmpegcore thumbnail \
  --input talk.mp4 \
  --output poster.jpg \
  --receipt run-receipt.json

pyffmpegcore receipt validate run-receipt.json
```

The job can fail and still produce a valid receipt. This is intentional: the
exit category and preflight/result facts are often most valuable when
diagnosing failure.

## Private by default

Schema `1.0` applies these transformations before the document can be written:

- absolute paths become `<path>/<basename>`;
- URL user information and fragments are removed;
- URL query strings become `<redacted>`;
- authorization, token, password, secret, and API-key values are redacted;
- probe summaries omit free-form media tags;
- content hashes are disabled.

Hashing can expose stable content identity and can be slow for large files. It
requires an explicit opt-in and records its algorithm:

```bash
pyffmpegcore convert \
  --input source.mov \
  --output publish.mp4 \
  --receipt run-receipt.json \
  --hash-content
```

The current algorithm is SHA-256. A receipt never contains media bytes.

## Bug reports without private media

Validate the receipt locally, then combine it with current `doctor` facts:

```bash
pyffmpegcore receipt bug-report run-receipt.json --output bug-report.json
```

This command does not open or probe the original input/output media. Review the
JSON before attaching it to an issue because filenames and technical metadata
can still be sensitive in some environments.

## Python

```python
from pyffmpegcore import ReceiptBuilder, WorkflowEngine

engine = WorkflowEngine()
plan = engine.planner.thumbnail("talk.mp4", "poster.jpg", timestamp="00:00:01")
batch = engine.run(plan)
receipt = ReceiptBuilder().build(batch)
receipt.write("run-receipt.json")
```

## Schema, examples, and migration

- [JSON Schema 1.0](schemas/run-receipt-1.0.schema.json)
- [Redacted example 1.0](schemas/run-receipt-1.0.example.json)

`schema_version` governs the stored receipt contract independently from the
package version. Additive fields may appear only when old consumers can ignore
them. Removing a field, changing its meaning/type, or weakening privacy
behavior requires a new schema and an explicit migration.

Version `1.0` is the first schema, so there is no historical conversion yet.
`pyffmpegcore receipt migrate INPUT [--output OUTPUT]` validates, re-applies
redaction, and emits canonical `1.0` JSON. It rejects unknown source or target
versions instead of guessing. Future migrations will be added behind this same
command and the `migrate_receipt()` Python function.
