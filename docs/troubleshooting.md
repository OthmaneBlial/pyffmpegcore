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

## Output already exists

The refusal is intentional. Choose a new output path or explicitly add `--force` after checking the target.

## A path contains spaces or apostrophes

Quote it in your shell. PyFFmpegCore passes paths as process arguments rather than shell strings:

```bash
pyffmpegcore probe --input "media/O'Brien clip.mp4"
```

## FFmpeg succeeds but PyFFmpegCore fails

Open a bug report with the exact PyFFmpegCore command, exit code, sanitized `doctor --json`, the raw FFmpeg command that succeeds, and a generated or redistribution-safe reproduction. See the [support guide](https://github.com/OthmaneBlial/pyffmpegcore/blob/main/SUPPORT.md).
