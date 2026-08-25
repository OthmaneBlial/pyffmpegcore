# Fit an upload under a target size

Two-pass compression estimates a video bitrate from duration, target bytes, audio bitrate, and container overhead. The target is practical, not a mathematical guarantee.

```bash
pyffmpegcore compress --input upload.mp4 --output upload-small.mp4 --target-size-kb 24576 --two-pass
pyffmpegcore probe --input upload-small.mp4 --json
```

For a quality-first output without an exact byte budget:

```bash
pyffmpegcore compress --input upload.mp4 --output upload-small.mp4 --crf 28
```

Verify the output byte size and decode it before deleting the source. Very small targets fail with a feasibility error rather than producing a known-invalid bitrate. Two-pass work creates temporary pass logs and cleans them after completion.
