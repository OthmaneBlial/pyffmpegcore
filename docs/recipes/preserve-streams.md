# Preserve every media stream

Use this when remuxing a rich media file and losing a second audio track,
subtitle, attachment, or data stream would be a failure.

FFmpeg's default stream selection normally chooses one stream of each supported
type. That behavior repeatedly surprises users working with multilingual and
captioned files: see the independent reports about [lost secondary tracks and
subtitles](https://superuser.com/questions/1513289/track-2-and-sub-titles-lost-in-ffmpeg-conversion),
[keeping every subtitle stream](https://superuser.com/questions/1406666/how-to-get-all-subtitle-streams-recorded-in-ffmpeg/1625114),
and [retaining multiple audio tracks](https://superuser.com/questions/811939/ffmpeg-convert-and-keep-audio-track).

## Inspect, explain, then copy

```bash
pyffmpegcore probe --input source.mkv --json

pyffmpegcore convert \
  --input source.mkv \
  --output preserved.mkv \
  --preserve-all-streams \
  --explain

pyffmpegcore convert \
  --input source.mkv \
  --output preserved.mkv \
  --preserve-all-streams \
  --receipt preserved.receipt.json

pyffmpegcore probe --input preserved.mkv --json
```

The plan explicitly maps input `0` and uses stream copy for every mapped
stream. Video and audio samples are not decoded or re-encoded. Compatible
format metadata and chapters are copied too, and an existing output is still
refused unless `--force` is explicit.

## Input and output contract

- Choose an output container that supports every input codec. Keeping the same
  container is the safest default; Matroska is usually a practical container
  for mixed stream types.
- `--preserve-all-streams` intentionally rejects `--audio-only`, codec,
  bitrate, thread, and hardware-acceleration options. Use the normal conversion
  path when re-encoding is the goal.
- Attachments and data streams are mapped as well as video, audio, and
  subtitles. Inspect the plan before writing.
- A container incompatibility is reported as a failed job; PyFFmpegCore does
  not silently drop the unsupported stream.

## Verify

Compare the before/after probes. The maintained real-media test asserts one
video stream, two differently tagged audio streams, one subtitle stream,
Unicode container metadata, and two chapters after the copy. The exact wheel
also runs this recipe on Linux, macOS, and Windows during release validation.

If you need to re-encode while making custom per-stream choices, use reviewed
raw FFmpeg for now and include the complete stream map in any recipe proposal.
