# Deterministic plans without shell strings

Every writing command compiles to an `ExecutionPlan` before execution. The plan
contains a version, workflow name, exact argument vector, selected inputs and
outputs, overwrite/timeout/temporary-file policy, required capabilities,
selected streams, operations, warnings, and structured metadata.

The executable receives an argument array directly. A safely escaped display is
for humans only; it is never evaluated by a shell. This keeps spaces,
apostrophes, Unicode, filter expressions, and untrusted path values from turning
into shell syntax.

```bash
pyffmpegcore thumbnail \
  --input "media/O'Brien clip.mp4" \
  --output "proof images/poster.jpg" \
  --timestamp 00:00:01 \
  --dry-run --plan-json
```

Plans are deterministic after normalizing environment-specific paths. CLI,
Python, examples, profiles, batches, and pipelines all consume the shared
planner rather than rebuilding commands. Versioned JSON and snapshot contracts
make an intentional plan change reviewable even when human wording evolves.

The low-level `FFmpegRunner.run(args)` remains available for experts, but raw
arguments deliberately do not inherit a workflow's preflight and output
contract.
