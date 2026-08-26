# Web-compatible video

Use this when an H.264/AAC MP4 is more portable than a source WebM or editor
export. This recipe responds to recurring reports where an MP4 [plays in VLC
but not in browsers](https://stackoverflow.com/questions/24693751/html5-video-ffmpeg-encoded-mp4-not-playing-in-any-browser-plays-in-vlc-though),
needs a [widely compatible pixel format](https://stackoverflow.com/questions/32829514/which-pixel-format-for-web-mp4-video),
or cannot start progressively because the [MP4 index is at the end](https://superuser.com/questions/851316/swapping-index-of-an-mp4-file-with-ffmpeg).

## CLI

```bash
pyffmpegcore probe --input input.webm
pyffmpegcore profile run web/mp4-compatible --input input.webm --output output.mp4 --explain
pyffmpegcore profile run web/mp4-compatible --input input.webm --output output.mp4 --receipt web.receipt.json
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

The output should probe as an MP4-family container with H.264 video, AAC audio
when the source has audio, YUV 4:2:0 pixels, and the `moov` atom before media
data for progressive download. The command re-encodes and selects the first
video/audio streams; it is not lossless. Use the [preserve every stream
recipe](preserve-streams.md) instead when remuxing a rich file without track
loss. Existing outputs require explicit CLI `--force`.

Media compatibility does not replace web-server correctness. Serve the file
with the appropriate `Content-Type` and byte-range support for the target
browser.

See the [dated before/after proof and redacted receipt](../evidence.md#reproducible-recipe-evidence).
