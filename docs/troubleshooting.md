# Troubleshooting

## Start with diagnostics

```bash
pyffmpegcore doctor --json
pyffmpegcore smoke-test
```

If either command fails, preserve the exit code and sanitized stderr. Do not post URL credentials, private paths, or personal metadata.

## `ffmpeg` or `ffprobe` is missing

Install both from your operating system's trusted package source, open a new terminal, and rerun `doctor`. An explicit path is supported:

```bash
pyffmpegcore --ffmpeg-path /trusted/path/ffmpeg --ffprobe-path /trusted/path/ffprobe doctor
```

## An encoder or filter is absent

FFmpeg builds differ. Inspect `doctor --json` and the workflow's error. Install an FFmpeg build that contains the required capability or choose a documented fallback. PyFFmpegCore does not silently download a codec build.

## A second audio track or subtitle disappeared

The normal `convert` workflow deliberately selects the first video and first
audio streams. FFmpeg users repeatedly encounter this implicit-selection trap
with [secondary tracks and subtitles](https://superuser.com/questions/1513289/track-2-and-sub-titles-lost-in-ffmpeg-conversion)
and [multilingual subtitle sets](https://superuser.com/questions/1808132/how-to-copy-the-video-covert-all-audio-streams-to-ac3-and-only-keep-the-subtit).

Probe before and after. If the goal is a lossless remux and the destination
container supports every source codec, use:

```bash
pyffmpegcore convert \
  --input source.mkv \
  --output preserved.mkv \
  --preserve-all-streams \
  --explain
```

Then execute the same command without `--explain`. See the [complete stream
preservation contract](recipes/preserve-streams.md). PyFFmpegCore fails rather
than silently dropping a stream that the output container cannot represent.

## The output is MP4 but a browser still refuses it

An `.mp4` suffix alone does not prove browser compatibility. Use the
[`web/mp4-compatible` recipe](recipes/web-video.md), probe the output, and also
verify the server's media `Content-Type` and byte-range behavior. Browser
reports commonly involve the [pixel format](https://stackoverflow.com/questions/32829514/which-pixel-format-for-web-mp4-video)
or [progressive-download index placement](https://superuser.com/questions/606653/ffmpeg-converting-media-type-aswell-as-relocating-moov-atom).

## A Python or background FFmpeg process appears to hang

Unconsumed FFmpeg output pipes and interactive stdin are recurring causes in
[Python subprocesses](https://stackoverflow.com/questions/40964071/piping-to-ffmpeg-with-python-subprocess-freezes)
and [background jobs](https://stackoverflow.com/questions/16523746/ffmpeg-hangs-when-run-in-background/16527559).
Managed PyFFmpegCore jobs continuously drain stdout/stderr, disable interactive
stdin, decode diagnostics as UTF-8 with replacement, and support a bounded
`--timeout`. Include a synthetic reproduction if a managed command still
stalls.

## Output already exists

The refusal is intentional. Choose a new output path or explicitly add `--force` after checking the target.

## A path contains spaces or apostrophes

Quote it in your shell. PyFFmpegCore passes paths as process arguments rather than shell strings:

```bash
pyffmpegcore probe --input "media/O'Brien clip.mp4"
```

## FFmpeg succeeds but PyFFmpegCore fails

Open a bug report with the exact PyFFmpegCore command, exit code, sanitized `doctor --json`, the raw FFmpeg command that succeeds, and a generated or redistribution-safe reproduction. See the [support guide](https://github.com/OthmaneBlial/pyffmpegcore/blob/main/SUPPORT.md).
