# PyFFmpegCore Examples

This file is a practical cookbook for people who want to use PyFFmpegCore with real files.

If you only read one rule, read this one:

**Do not feel forced to run every example script exactly as-is.** Some `main()` functions are simple demonstrations with placeholder filenames. For real work, copy the function examples below and replace the sample paths with your own files.

## Start Here

Set up a local environment:

```bash
python -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
```

Make sure FFmpeg is installed:

```bash
ffmpeg -version
ffprobe -version
```

Download the same real sample files used in integration tests:

```bash
python tests/media/download_fixtures.py
```

The code blocks below that import from `examples.*` assume you are running them from a clone of this repository.

You will then have these practice files in `tests/media/downloads/`:

| Sample file | What it represents |
| --- | --- |
| `sample_mp4_h264.mp4` | a normal MP4 clip with video and audio |
| `sample_webm_vp9.webm` | a web video you want to convert |
| `sample_video_mov.mov` | a camera or editor export |
| `sample_audio_mp3.mp3` | a song, voice-over, or podcast clip |
| `sample_audio_wav.wav` | a raw or uncompressed audio recording |
| `sample_image_png.png` | a graphic or screenshot |
| `sample_image_jpg.jpg` | a photo |
| `sample_subtitles.srt` | a subtitle or caption file |

## How To Replace The Sample Files With Your Own

The examples below use the tested sample files because they are known to work.

To use your own media:

- replace the input path with your own file path
- keep the output path as any new filename you want
- keep the output extension matched to the result you want

Examples:

- `tests/media/downloads/sample_mp4_h264.mp4` -> `wedding/highlight.mp4`
- `tests/media/downloads/sample_audio_mp3.mp3` -> `podcast/intro-music.mp3`
- `tests/media/downloads/sample_subtitles.srt` -> `captions/english.srt`

## Example 1: Convert A Video To MP4

Use this when you have a WebM, MOV, or another format and want a standard MP4.

Real tested input:

- `tests/media/downloads/sample_webm_vp9.webm`

```python
from pyffmpegcore import FFmpegRunner

ffmpeg = FFmpegRunner()

result = ffmpeg.convert(
    "tests/media/downloads/sample_webm_vp9.webm",
    "converted.mp4",
    video_codec="libx264",
    audio_codec="aac",
)

print("Success" if result.returncode == 0 else result.stderr)
```

Use your own files the same way:

- `camera-export.mov` -> `camera-export.mp4`
- `downloaded-video.webm` -> `downloaded-video.mp4`

## Example 2: Inspect A File Before Editing It

Use this when you want to know the duration, resolution, codecs, or bitrate before doing anything else.

Real tested input:

- `tests/media/downloads/sample_mp4_h264.mp4`

```python
from pyffmpegcore import FFprobeRunner

ffprobe = FFprobeRunner()
info = ffprobe.probe("tests/media/downloads/sample_mp4_h264.mp4")

print(info["filename"])
print(info["duration"])
print(info["video"]["width"], info["video"]["height"])
print(info["video"]["codec"])
print(info["audio"]["codec"])
```

This is a good first step if you are not sure what kind of media file you have.

## Example 3: Compress A Video

Use this when a video is too large to upload, email, or archive comfortably.

Real tested input:

- `tests/media/downloads/sample_mp4_h264.mp4`

```python
from pyffmpegcore import FFmpegRunner

ffmpeg = FFmpegRunner()

result = ffmpeg.compress(
    "tests/media/downloads/sample_mp4_h264.mp4",
    "compressed.mp4",
    crf=28,
    two_pass=False,
)

print("Success" if result.returncode == 0 else result.stderr)
```

If you care about hitting a specific file size, use `target_size_kb=` and keep `two_pass=True`.

## Example 4: Extract Audio From A Video

Use this when you want the speech, interview audio, or soundtrack as a separate file.

Real tested input:

- `tests/media/downloads/sample_mp4_h264.mp4`

```python
from pyffmpegcore import FFmpegRunner

ffmpeg = FFmpegRunner()

result = ffmpeg.extract_audio(
    "tests/media/downloads/sample_mp4_h264.mp4",
    "audio-only.mp3",
)

print("Success" if result.returncode == 0 else result.stderr)
```

Common real-world outputs:

- `lecture.mp4` -> `lecture.mp3`
- `interview.mov` -> `interview.wav`

## Example 5: Create Thumbnails From A Video

Use this for previews, gallery cards, posters, or upload thumbnails.

Real tested input:

- `tests/media/downloads/sample_mp4_h264.mp4`

```python
from examples.extract_thumbnail import extract_thumbnail, extract_multiple_thumbnails

extract_thumbnail(
    "tests/media/downloads/sample_mp4_h264.mp4",
    "thumbnail.jpg",
    timestamp="00:00:01",
    width=640,
)

extract_multiple_thumbnails(
    "tests/media/downloads/sample_mp4_h264.mp4",
    "thumbs",
    ["00:00:01", "00:00:02", "00:00:03"],
    width=320,
)
```

Use your own video exactly the same way.

## Example 6: Speed Up Or Slow Down A Video

Use this for time-lapse style output, quick previews, or slow-motion effects.

Real tested input:

- `tests/media/downloads/sample_mp4_h264.mp4`

```python
from examples.adjust_video_speed import change_video_speed

change_video_speed(
    "tests/media/downloads/sample_mp4_h264.mp4",
    "faster.mp4",
    1.5,
)
```

Examples of your own files:

- `walkthrough.mp4` -> `walkthrough-fast.mp4`
- `action-shot.mp4` -> `action-shot-slow.mp4`

## Example 7: Join Clips Together

Use this when you recorded several short clips and want one combined video.

For clips that already match in format and codecs, use the fast stream-copy version:

```python
from examples.concatenate_videos import concatenate_videos_basic

concatenate_videos_basic(
    [
        "tests/media/downloads/sample_mp4_h264.mp4",
        "tests/media/downloads/sample_mp4_h264.mp4",
    ],
    "joined.mp4",
)
```

For mixed sources, use the safer re-encode version:

```python
from examples.concatenate_videos import concatenate_videos_reencode

concatenate_videos_reencode(
    [
        "tests/media/downloads/sample_mp4_h264.mp4",
        "tests/media/downloads/sample_webm_vp9.webm",
    ],
    "joined-reencoded.mp4",
)
```

Real-world examples:

- `part1.mp4`, `part2.mp4`, `part3.mp4` -> `full-video.mp4`
- `intro.mov`, `screen-recording.webm` -> `combined.mp4`

## Example 8: Add, Extract, Or Burn Subtitles

Use these workflows when you have an `.srt` subtitle file.

Real tested files:

- `tests/media/downloads/sample_mp4_h264.mp4`
- `tests/media/downloads/sample_subtitles.srt`

Add subtitles as a selectable track:

```python
from examples.handle_subtitles import add_subtitle_track

add_subtitle_track(
    "tests/media/downloads/sample_mp4_h264.mp4",
    "tests/media/downloads/sample_subtitles.srt",
    "with-subtitles.mp4",
)
```

Extract subtitles from a video that already contains them:

```python
from examples.handle_subtitles import extract_subtitles

extract_subtitles(
    "with-subtitles.mp4",
    "extracted.srt",
)
```

Burn subtitles permanently into the picture:

```python
from examples.handle_subtitles import burn_subtitles

burn_subtitles(
    "tests/media/downloads/sample_mp4_h264.mp4",
    "tests/media/downloads/sample_subtitles.srt",
    "burned-subtitles.mp4",
)
```

Use subtitle burning when you want captions always visible. Use a subtitle track when you want viewers to be able to turn captions on or off.

## Example 9: Mix Two Audio Files

Use this when you want voice plus music, or two music sources together.

Real tested files:

- `tests/media/downloads/sample_audio_mp3.mp3`
- `tests/media/downloads/sample_audio_wav.wav`

```python
from examples.mix_audio import add_background_music, mix_audio_files

mix_audio_files(
    [
        "tests/media/downloads/sample_audio_mp3.mp3",
        "tests/media/downloads/sample_audio_wav.wav",
    ],
    "mixed.mp3",
    volumes=[1.0, 0.4],
)

add_background_music(
    "tests/media/downloads/sample_audio_mp3.mp3",
    "tests/media/downloads/sample_audio_wav.wav",
    "voice-plus-music.mp3",
    bg_volume=0.25,
)
```

Real-world examples:

- `voiceover.mp3` plus `music-bed.wav`
- `podcast.wav` plus `intro-theme.mp3`

## Example 10: Normalize Audio Levels

Use this when your audio is too quiet, too uneven, or inconsistent between tracks.

Real tested input:

- `tests/media/downloads/sample_audio_mp3.mp3`

```python
from examples.normalize_audio import normalize_audio_loudnorm, create_mastered_audio

normalize_audio_loudnorm(
    "tests/media/downloads/sample_audio_mp3.mp3",
    "normalized.mp3",
)

create_mastered_audio(
    "tests/media/downloads/sample_audio_mp3.mp3",
    "mastered.mp3",
)
```

`normalize_audio_loudnorm()` is the safer first step for most people. `create_mastered_audio()` adds a fuller mastering chain.

## Example 11: Turn Audio Into A Waveform Image

Use this for podcast pages, audio previews, or visual summaries of sound.

Real tested input:

- `tests/media/downloads/sample_audio_mp3.mp3`

```python
from examples.generate_waveform import (
    generate_waveform_image,
    generate_waveform_with_metadata,
)

generate_waveform_image(
    "tests/media/downloads/sample_audio_mp3.mp3",
    "waveform.png",
    width=1000,
    height=300,
)

generate_waveform_with_metadata(
    "tests/media/downloads/sample_audio_mp3.mp3",
    "waveform-output",
)
```

## Example 12: Batch Convert Or Optimize Images

Use this when you have a folder full of screenshots, product photos, or graphics.

Real tested inputs:

- `tests/media/downloads/sample_image_png.png`
- `tests/media/downloads/sample_image_jpg.jpg`

```python
from examples.batch_convert_images import (
    batch_convert_images,
    convert_to_webp_batch,
    optimize_images_for_web,
)

batch_convert_images(
    "tests/media/downloads",
    "converted-images",
    output_format="jpg",
    quality=80,
)

optimize_images_for_web(
    "tests/media/downloads",
    "web-images",
    max_width=1280,
    max_height=1280,
    quality=80,
)

convert_to_webp_batch(
    "tests/media/downloads",
    "webp-images",
    quality=75,
)
```

In normal use, point these functions at a folder that contains only the images you want to process.

## Which Examples Are Backed By Real Tests

These are the example modules with real-media coverage in this repository:

| Example file | Verified workflows |
| --- | --- |
| `examples/convert_video.py` | converting a real downloaded video into MP4 |
| `examples/extract_metadata.py` | probing a real MP4 and printing expected metadata |
| `examples/compress_with_progress.py` | compressing a real MP4 while emitting progress |
| `examples/extract_thumbnail.py` | creating real thumbnail files from video |
| `examples/generate_waveform.py` | creating real waveform images and metadata overlays |
| `examples/concatenate_videos.py` | joining real videos, including path edge cases |
| `examples/handle_subtitles.py` | subtitle track add, extract, and burn workflows |
| `examples/mix_audio.py` | mixing, merging, mashup, and background music workflows |
| `examples/normalize_audio.py` | loudness normalization and mastered output |
| `examples/batch_convert_images.py` | PNG, JPG, WebP conversion and broken-file reporting |
| `examples/adjust_video_speed.py` | faster and slower output on real media |

## Safe Advice For Non-Technical Users

- start with one short test file, not your biggest important file
- write output to a new filename, not over your only copy
- open the output afterward in your normal media player
- if you join clips and the fast concat version fails, switch to the re-encode version
- if something feels unclear, start from the smaller examples in `README.md` first
