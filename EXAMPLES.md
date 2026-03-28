# CLI Examples

This file is the practical cookbook for the `pyffmpegcore` command.

If you only remember one rule, remember this:

**Replace the sample input path with your own file, keep the output path as a new filename, and keep the output extension matched to the result you want.**

## Before You Start

Install the CLI and make sure FFmpeg is available:

```bash
pyffmpegcore --version
pyffmpegcore doctor
```

If you want the exact practice files used in real tests:

```bash
python tests/media/download_fixtures.py
```

You will then have these sample files:

| Sample file | Real-world equivalent |
| --- | --- |
| `tests/media/downloads/sample_mp4_h264.mp4` | a normal phone clip or exported MP4 |
| `tests/media/downloads/sample_webm_vp9.webm` | a browser download or recorded web video |
| `tests/media/downloads/sample_video_mov.mov` | a camera or editor export |
| `tests/media/downloads/sample_audio_mp3.mp3` | a podcast, music file, or voice-over |
| `tests/media/downloads/sample_audio_wav.wav` | a raw recording |
| `tests/media/downloads/sample_image_png.png` | a screenshot or graphic |
| `tests/media/downloads/sample_image_jpg.jpg` | a photo |
| `tests/media/downloads/sample_subtitles.srt` | a subtitle file |

## Example 1: Inspect A File First

Use this when you do not know the duration, resolution, or codecs yet.

```bash
pyffmpegcore probe --input tests/media/downloads/sample_mp4_h264.mp4
```

Use your own file the same way:

```bash
pyffmpegcore probe --input "my holiday clip.mp4"
```

## Example 2: Convert WebM To MP4

Use this when a site or app gave you a `.webm` but you want a normal `.mp4`.

```bash
pyffmpegcore convert \
  --input tests/media/downloads/sample_webm_vp9.webm \
  --output converted.mp4 \
  --video-codec libx264 \
  --audio-codec aac
```

Real-world version:

```bash
pyffmpegcore convert --input "downloaded-video.webm" --output "downloaded-video.mp4" --video-codec libx264 --audio-codec aac
```

## Example 3: Convert MOV To MP4

Use this for camera exports or editor exports.

```bash
pyffmpegcore convert \
  --input tests/media/downloads/sample_video_mov.mov \
  --output camera-export.mp4 \
  --video-codec libx264 \
  --audio-codec aac
```

## Example 4: Compress A Large Video

Use this when a video is too large to upload or share comfortably.

```bash
pyffmpegcore compress \
  --input tests/media/downloads/sample_mp4_h264.mp4 \
  --output compressed.mp4 \
  --crf 28
```

Real-world version:

```bash
pyffmpegcore compress --input "full-event.mp4" --output "full-event-smaller.mp4" --crf 28
```

## Example 5: Extract MP3 Audio From A Video

Use this when you want only the speech, soundtrack, or interview audio.

```bash
pyffmpegcore extract-audio \
  --input tests/media/downloads/sample_mp4_h264.mp4 \
  --output audio-only.mp3
```

Real-world version:

```bash
pyffmpegcore extract-audio --input lecture.mp4 --output lecture.mp3
```

## Example 6: Extract WAV Audio Instead

Use WAV when you want an uncompressed result for editing.

```bash
pyffmpegcore extract-audio \
  --input tests/media/downloads/sample_mp4_h264.mp4 \
  --output audio-only.wav
```

## Example 7: Make A Thumbnail

Use this for previews, gallery cards, or video cover images.

```bash
pyffmpegcore thumbnail \
  --input tests/media/downloads/sample_mp4_h264.mp4 \
  --output thumbnail.jpg \
  --timestamp 00:00:01 \
  --width 640
```

Real-world version:

```bash
pyffmpegcore thumbnail --input "podcast-video.mp4" --output "podcast-cover.jpg" --timestamp 00:00:12 --width 1280
```

## Example 8: Generate A Waveform

Use this for podcast pages, music previews, or audio dashboards.

```bash
pyffmpegcore waveform \
  --input tests/media/downloads/sample_audio_mp3.mp3 \
  --output waveform.png \
  --width 1200 \
  --height 300
```

Real-world version:

```bash
pyffmpegcore waveform --input "episode-intro.mp3" --output "episode-intro-waveform.png" --width 1600 --height 400
```

## Example 9: Speed Up A Video

Use this for quick previews or time-lapse style output.

```bash
pyffmpegcore speed video \
  --input tests/media/downloads/sample_mp4_h264.mp4 \
  --output faster.mp4 \
  --factor 1.5
```

## Example 10: Slow Down A Video

Use this for slow-motion style output.

```bash
pyffmpegcore speed video \
  --input tests/media/downloads/sample_mp4_h264.mp4 \
  --output slower.mp4 \
  --factor 0.75
```

## Example 11: Change Audio Speed

Use this for spoken-word practice files or fast review copies.

```bash
pyffmpegcore speed audio \
  --input tests/media/downloads/sample_audio_mp3.mp3 \
  --output faster-audio.mp3 \
  --factor 1.25
```

## Example 12: Join Matching MP4 Clips Quickly

Use `--mode copy` only when the clips already match well.

```bash
pyffmpegcore concat \
  --inputs tests/media/downloads/sample_mp4_h264.mp4 tests/media/downloads/sample_mp4_h264.mp4 \
  --output joined.mp4 \
  --mode copy
```

Real-world version:

```bash
pyffmpegcore concat --inputs part1.mp4 part2.mp4 part3.mp4 --output full-video.mp4 --mode copy
```

## Example 13: Join Mixed Clips More Safely

Use `--mode reencode` when the sources do not already match.

```bash
pyffmpegcore concat \
  --inputs tests/media/downloads/sample_mp4_h264.mp4 tests/media/downloads/sample_webm_vp9.webm \
  --output joined-safe.mp4 \
  --mode reencode
```

## Example 14: Add A Subtitle Track

Use this when you want a subtitle track people can turn on or off.

```bash
pyffmpegcore subtitles add \
  --video tests/media/downloads/sample_mp4_h264.mp4 \
  --subtitle tests/media/downloads/sample_subtitles.srt \
  --output with-subtitles.mp4
```

## Example 15: Extract A Subtitle Track

Use this when a video already contains subtitles and you want them as a file.

```bash
pyffmpegcore subtitles extract \
  --video with-subtitles.mp4 \
  --output extracted.srt
```

## Example 16: Burn Subtitles Into The Video

Use this when you want the subtitle text permanently visible.

```bash
pyffmpegcore subtitles burn \
  --video tests/media/downloads/sample_mp4_h264.mp4 \
  --subtitle tests/media/downloads/sample_subtitles.srt \
  --output burned-subtitles.mp4
```

## Example 17: Mix Two Audio Files Together

Use this when you want two tracks playing at the same time.

```bash
pyffmpegcore mix-audio mix \
  --inputs tests/media/downloads/sample_audio_mp3.mp3 tests/media/downloads/sample_audio_wav.wav \
  --output mixed-audio.wav
```

## Example 18: Add Background Music Under Speech

Use this when you want a main voice track plus quieter music underneath.

```bash
pyffmpegcore mix-audio background \
  --main-input tests/media/downloads/sample_audio_wav.wav \
  --background-input tests/media/downloads/sample_audio_mp3.mp3 \
  --output background-mix.wav \
  --bg-volume 0.2
```

## Example 19: Normalize Audio Loudness

Use this when a recording is too quiet, too loud, or inconsistent.

```bash
pyffmpegcore normalize-audio \
  --input tests/media/downloads/sample_audio_mp3.mp3 \
  --output normalized.wav
```

## Example 20: Convert PNG And JPG Images To JPG

Use this when you have a folder of mixed images and want consistent JPG outputs.

```bash
mkdir -p demo-images
cp tests/media/downloads/sample_image_png.png demo-images/
cp tests/media/downloads/sample_image_jpg.jpg demo-images/
pyffmpegcore images convert --input-dir demo-images --output-dir converted-images --format jpg
```

## Example 21: Optimize Images For The Web

Use this when you want resized, web-friendly image outputs.

```bash
pyffmpegcore images optimize \
  --input-dir demo-images \
  --output-dir optimized-images \
  --max-width 1600 \
  --max-height 900
```

## Example 22: Convert Images To WebP

Use this when you want smaller web image outputs.

```bash
pyffmpegcore images webp \
  --input-dir demo-images \
  --output-dir webp-images \
  --quality 80
```

## Command Help

Every command has built-in help:

```bash
pyffmpegcore --help
pyffmpegcore compress --help
pyffmpegcore subtitles --help
pyffmpegcore mix-audio background --help
```

## If You Prefer Python

The CLI is now the main onboarding path, but the Python API still exists.

See the Python section in `README.md` if you want to call `FFmpegRunner` directly from code.
