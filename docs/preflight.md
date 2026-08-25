# Capability-aware preflight

`PreflightEngine` checks an `ExecutionPlan` without creating an output directory, temporary file, or media output.

It checks:

- the selected FFmpeg executable;
- local input existence/readability or URL protocol support;
- required video, audio, or subtitle streams;
- encoders, decoders, filters, muxers, demuxers, protocols, and hardware requirements;
- output-container support inferred from the extension;
- writable output parents and existing-output collisions;
- free disk space against a plan estimate.

```python
from pyffmpegcore import ExecutionPlan, PreflightEngine

plan = ExecutionPlan(
    workflow="thumbnail",
    command=("ffmpeg", "-i", "/media/input.mp4", "-frames:v", "1", "/media/thumb.jpg"),
    inputs=("/media/input.mp4",),
    outputs=("/media/thumb.jpg",),
    required_capabilities=("filter:scale", "muxer:image2"),
    metadata={"required_stream_types": ["video"]},
)
report = PreflightEngine().check(plan)
print(report.render())
print(report.to_dict())
```

Human and JSON rendering come from the same immutable checks. JSON uses `schema_version: "1.0"`. A missing capability names the exact `kind:name` requirement and provides either an available maintained fallback or an OS-specific installation remedy.

The workflow-rule catalog lives in `pyffmpegcore.capabilities.WORKFLOW_CAPABILITY_RULES`. Plans may add stricter requirements; they cannot remove the workflow baseline.
