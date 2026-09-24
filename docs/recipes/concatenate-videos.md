# Join video clips

Choose `--mode copy` when clips have matching stream layouts. It avoids
re-encoding. Choose `--mode reencode` when codecs or containers differ and each
clip has one video stream, one audio stream, and the same video dimensions.

## Stream copy

Preview the metadata check before writing:

```bash
pyffmpegcore concat --mode copy --inputs "part one.mp4" part-two.mp4 --output joined.mp4 --explain
```

Preflight compares stream order, types, codecs, profiles, dimensions, audio
properties, and available time-base/pixel-format metadata. The FFmpeg concat
demuxer requires matching streams, codecs, and time bases. Matching probe facts
cannot prove packet-level compatibility, so inspect the result and keep the
source clips. Remote inputs receive a warning because preflight cannot compare
their stream metadata.

## Re-encode

```bash
pyffmpegcore concat --mode reencode --inputs h264.mp4 vp9.webm --output joined.mp4 --explain
```

This mode selects the first video and audio stream from each input, resets
timestamps, joins synchronized audio/video segments, and encodes H.264/AAC by
default. It supports codec and container differences when stream layouts and
video dimensions match. Preflight rejects different video dimensions before
writing; resize clips to a common size first. Every input must contain video
and audio. Other tracks are omitted; preflight warns when it finds extra tracks
or cannot inspect a remote input. FFmpeg's concat-filter requirements are
described in its [filter documentation](https://ffmpeg.org/ffmpeg-filters.html#concat).

After reviewing the plan, run the same command without `--explain` and add a
receipt:

```bash
pyffmpegcore concat --mode reencode --inputs h264.mp4 vp9.webm --output joined.mp4 --receipt joined.receipt.json
pyffmpegcore probe --input joined.mp4 --json
pyffmpegcore receipt validate joined.receipt.json --json
```

The output path is never overwritten without `--force`. The stream-copy
demuxer contract is documented in the [FFmpeg format reference](https://ffmpeg.org/ffmpeg-formats.html#concat-1).
