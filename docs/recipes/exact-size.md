# Fit an upload under a target size

Two-pass compression estimates a video bitrate from duration, target bytes, audio bitrate, and container overhead. The target is practical, not a mathematical guarantee.

This answers a repeated constraint rather than promising magic compression:
users ask how to [encode to a specific size](https://stackoverflow.com/questions/29082422/ffmpeg-video-compression-specific-file-size/61146975),
how to [avoid clipping while staying under a limit](https://stackoverflow.com/questions/68608701/targeting-a-specific-file-size-in-vp8vorbis-encoding-using-ffmpeg),
and why FFmpeg's hard [`-fs` limit is not exact](https://stackoverflow.com/questions/59051058/limit-file-size-in-ffmpeg).

```bash
pyffmpegcore compress --input upload.mp4 --output upload-small.mp4 --target-size 24MiB --two-pass --receipt upload.json
pyffmpegcore probe --input upload-small.mp4 --json
```

For a quality-first output without an exact byte budget:

```bash
pyffmpegcore compress --input upload.mp4 --output upload-small.mp4 --crf 28
```

Choose one primary goal: use CRF when visual quality matters more than final
bytes, and two-pass target-size mode when an upload or storage ceiling is the
hard constraint.

Completed target-size jobs print a measured proof using the actual source,
output, and limit, for example `Target-size proof: INPUT -> OUTPUT; limit
LIMIT; PASS`. The same byte counts and `target_met` boolean are present in
`--result-json` and the optional receipt.

FFmpeg can finish encoding while the measured result says `MISS`. The command
exit status reports execution, not whether the byte limit was met. CI and other
automations must check `target_met` before accepting the output.

Very small targets fail before mutation with a human-readable minimum size at
the selected `--min-video-bitrate` quality floor. Two-pass work creates
temporary pass logs and cleans them after completion. Decode and review the
result before deleting the source; meeting a byte limit does not itself prove
subjective quality.

For target-size plans, FFprobe reads source duration and streams. Video-only
input reserves no audio bitrate and does not require an audio encoder.

The default reserves 5% for muxing overhead. Advanced users can override it
with `--container-overhead-percent`; a larger reserve can help when a measured
run misses its cap. On one public-domain 720p sample, 5% missed by 7,803 bytes
and an explicit 7% passed. This result depends on input and FFmpeg build; see
the [dated receipt and quality check](../evidence.md#public-domain-exact-size-check-on-24-september-2026).

See the [dated target-size proof and redacted receipt](../evidence.md#reproducible-recipe-evidence).
