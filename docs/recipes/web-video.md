# Web-compatible video

Use this when an H.264/AAC MP4 is more portable than a source WebM or editor export.

## CLI

```bash
pyffmpegcore probe --input input.webm
pyffmpegcore convert --input input.webm --output output.mp4 --video-codec libx264 --audio-codec aac
pyffmpegcore probe --input output.mp4 --json
```

PowerShell uses the same arguments. Quote Windows paths containing spaces.

## Python

```python
from pyffmpegcore import FFmpegRunner

result = FFmpegRunner().convert(
    "input.webm",
    "output.mp4",
    video_codec="libx264",
    audio_codec="aac",
)
if result.returncode != 0:
    raise RuntimeError(result.stderr)
```

## Verify

The output should probe as an MP4-family container with H.264 video and AAC audio when the source has audio. The command re-encodes; it is not lossless. Existing outputs require explicit CLI `--force`.
