# Fit an upload under a target size

Two-pass compression estimates a video bitrate from duration, target bytes, audio bitrate, and container overhead. The target is practical, not a mathematical guarantee.

```bash
pyffmpegcore compress --input upload.mp4 --output upload-small.mp4 --target-size 24MiB --two-pass --receipt upload.json
pyffmpegcore probe --input upload-small.mp4 --json
```

For a quality-first output without an exact byte budget:

```bash
pyffmpegcore compress --input upload.mp4 --output upload-small.mp4 --crf 28
```

Successful target-size jobs print a measured proof using the actual source,
output, and limit, for example `Target-size proof: INPUT -> OUTPUT; limit
LIMIT; PASS`. The same byte counts and `target_met` boolean are present in
`--result-json` and the optional receipt.

Very small targets fail before mutation with a human-readable minimum size at
the selected `--min-video-bitrate` quality floor. Two-pass work creates
temporary pass logs and cleans them after completion. Decode and review the
result before deleting the source; meeting a byte limit does not itself prove
subjective quality.

The default reserves a conservative 5% for muxing overhead. Advanced users can
override it with `--container-overhead-percent`; lowering the reserve can move
the result closer to the limit but increases the risk of a reported `MISS`.

See the [dated target-size proof and redacted receipt](../evidence.md#reproducible-recipe-evidence).
