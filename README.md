# PyFFmpegCore

A small Python wrapper around `ffmpeg` and `ffprobe` for everyday media jobs.

Use it when you want to:

- convert a video to another format
- compress a large video
- extract audio from a video
- grab thumbnails from a video
- speed up or slow down media
- join clips together
- add or burn subtitles
- mix or normalize audio
- convert images in batches

[![PyPI version](https://badge.fury.io/py/pyffmpegcore.svg)](https://pypi.org/project/pyffmpegcore/)
[![Python versions](https://img.shields.io/pypi/pyversions/pyffmpegcore.svg)](https://pypi.org/project/pyffmpegcore/)
[![License](https://img.shields.io/pypi/l/pyffmpegcore.svg)](https://pypi.org/project/pyffmpegcore/)

## What This Project Is

PyFFmpegCore is a Python library, not a drag-and-drop desktop app.

It gives you simple Python functions on top of `ffmpeg`, which is the real tool that does the media work in the background. If you can point to a video, audio file, subtitle file, or image, PyFFmpegCore helps you run common workflows with less FFmpeg command-line complexity.

## What Is Proven To Work

As of March 28, 2026, this repository was validated locally with:

- Python `3.12`
- `ffmpeg` and `ffprobe` available on `PATH`
- `105` passing tests
- real downloaded media files, not only mocks
- end-to-end checks for video, audio, subtitles, waveforms, and image conversion
- path handling for spaces and apostrophes in important workflows

The deepest local validation was run on Linux. A final acceptance pass also downloaded a fresh set of sample files into a clean temporary folder and re-ran the main workflows there.

## Before You Start

You need:

- Python `3.10+`
- `ffmpeg`
- `ffprobe`

Then install the package:

```bash
pip install pyffmpegcore
```

If you want to run the examples from this repository:

```bash
python -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
```

Check that FFmpeg is really installed:

```bash
ffmpeg -version
ffprobe -version
```

## Practice With The Same Real Files Used In Tests

If you want a safe starting point, download the same sample files this repo uses in real validation:

```bash
python tests/media/download_fixtures.py
```

That creates files under `tests/media/downloads/`.

These are the main practice files:

| File | What it is | Real-world equivalent |
| --- | --- | --- |
| `tests/media/downloads/sample_mp4_h264.mp4` | 5-second MP4 video with audio | a phone clip, screen recording, or short exported video |
| `tests/media/downloads/sample_webm_vp9.webm` | 5-second WebM video | a browser-recorded or downloaded web video |
| `tests/media/downloads/sample_video_mov.mov` | MOV video | a camera or editor export |
| `tests/media/downloads/sample_audio_mp3.mp3` | MP3 audio | a voice-over, song, or podcast snippet |
| `tests/media/downloads/sample_audio_wav.wav` | WAV audio | an uncompressed recording |
| `tests/media/downloads/sample_image_png.png` | PNG image | a graphic, screenshot, or design asset |
| `tests/media/downloads/sample_image_jpg.jpg` | JPG image | a photo |
| `tests/media/downloads/sample_subtitles.srt` | SRT subtitles | captions you want to attach to a video |

If you already have your own files, you can skip this step and replace the sample paths below with your own paths.

## Quick Start

### 1. Convert a video to MP4

Real tested input:

- `tests/media/downloads/sample_webm_vp9.webm`

Use your own file instead if you want, for example `holiday-video.webm` or `camera-export.mov`.

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

### 2. Read the metadata of a media file

This is useful before editing because it tells you the duration, size, resolution, and codecs.

```python
from pyffmpegcore import FFprobeRunner

ffprobe = FFprobeRunner()
info = ffprobe.probe("tests/media/downloads/sample_mp4_h264.mp4")

print(f"Duration: {info['duration']:.2f} seconds")
print(f"Resolution: {info['video']['width']}x{info['video']['height']}")
print(f"Video codec: {info['video']['codec']}")
print(f"Audio codec: {info['audio']['codec']}")
```

### 3. Compress a video and keep progress updates

This is the typical “my video file is too big” workflow.

```python
from pyffmpegcore import FFmpegRunner, FFprobeRunner, ProgressCallback

ffmpeg = FFmpegRunner()
ffprobe = FFprobeRunner()
duration = ffprobe.get_duration("tests/media/downloads/sample_mp4_h264.mp4")

result = ffmpeg.compress(
    "tests/media/downloads/sample_mp4_h264.mp4",
    "compressed.mp4",
    crf=28,
    progress_callback=ProgressCallback(total_duration=duration),
)

print("Success" if result.returncode == 0 else result.stderr)
```

### 4. Extract audio from a video

This is useful when you want the speech, music, or soundtrack as a separate file.

```python
from pyffmpegcore import FFmpegRunner

ffmpeg = FFmpegRunner()

result = ffmpeg.extract_audio(
    "tests/media/downloads/sample_mp4_h264.mp4",
    "audio-only.mp3",
)

print("Success" if result.returncode == 0 else result.stderr)
```

### 5. Create a thumbnail image from a video

This is useful for previews, thumbnails, and poster frames.

```python
from pyffmpegcore import FFmpegRunner

ffmpeg = FFmpegRunner()

result = ffmpeg.extract_thumbnail(
    "tests/media/downloads/sample_mp4_h264.mp4",
    "thumbnail.jpg",
    timestamp="00:00:01",
    width=640,
)

print("Success" if result.returncode == 0 else result.stderr)
```

### 6. Make a waveform image from audio

This is useful for podcasts, music previews, and audio dashboards.

```python
from pyffmpegcore import FFmpegRunner

ffmpeg = FFmpegRunner()

result = ffmpeg.generate_waveform(
    "tests/media/downloads/sample_audio_mp3.mp3",
    "waveform.png",
    width=1000,
    height=300,
    colors="white",
)

print("Success" if result.returncode == 0 else result.stderr)
```

## Use Your Own Files

You do not need to rename your files to the sample names.

Replace the sample paths with your own, for example:

- `tests/media/downloads/sample_mp4_h264.mp4` -> `my-trip-video.mp4`
- `tests/media/downloads/sample_audio_mp3.mp3` -> `podcast-intro.mp3`
- `tests/media/downloads/sample_subtitles.srt` -> `english-captions.srt`

Good rules to follow:

- choose the output extension you want, such as `.mp4`, `.mp3`, `.wav`, `.jpg`, or `.webp`
- if you join clips with stream copy, use clips that already match well in format and codecs
- if your clips are mixed formats, use the re-encode concat example in [EXAMPLES.md](EXAMPLES.md)
- if you burn subtitles, use an `.srt` file to start with
- after each run, open the output file in your normal media player to confirm it looks and sounds right

## Main Python APIs

### `FFmpegRunner`

Common methods:

- `convert(input_file, output_file, progress_callback=None, audio_only=False, **kwargs)`
- `resize(input_file, output_file, width, height, progress_callback=None, **kwargs)`
- `compress(input_file, output_file, target_size_kb=None, crf=23, two_pass=True, progress_callback=None, **kwargs)`
- `extract_audio(input_file, output_file, progress_callback=None, **kwargs)`
- `extract_thumbnail(input_file, output_file, timestamp="00:00:01", width=320, height=None, quality=2)`
- `adjust_speed(input_file, output_file, speed_factor=1.0, audio_pitch=True)`
- `generate_waveform(input_file, output_file, width=800, height=200, colors="white")`

Useful kwargs:

- `video_codec`
- `audio_codec`
- `video_bitrate`
- `audio_bitrate`
- `preset`
- `pix_fmt`
- `threads`
- `movflags`
- `sample_rate`
- `channels`

### `FFprobeRunner`

Useful methods:

- `probe(input_file)`
- `get_duration(input_file)`
- `get_resolution(input_file)`
- `get_bitrate(input_file)`

`probe()` returns a simplified Python dictionary with the fields most people need first.

### `ProgressCallback`

Use `ProgressCallback` when you want progress updates during long FFmpeg jobs.

## Where To Find Real Working Examples

Start with [EXAMPLES.md](EXAMPLES.md) if you want task-based recipes such as:

- join several clips into one video
- add subtitles as a selectable track
- burn subtitles into the picture
- mix voice and background music
- normalize audio loudness
- batch convert PNG and JPG images

The larger recipes in `EXAMPLES.md` import helper functions from the repository's `examples/` folder, so they are meant for people working from a cloned checkout of this repo.

## Development

The local development workflow is documented in [DEVELOPMENT.md](DEVELOPMENT.md).

Main validation commands:

```bash
python -m compileall pyffmpegcore tests examples
python -m pytest
python -m build
```

## Practical Notes

- The first real-media test run may download sample files from the internet.
- Downloaded fixtures are ignored by git and stored under `tests/media/downloads/`.
- Some larger example scripts still include demonstration `main()` functions with placeholder filenames. For real use, the function-style examples in [EXAMPLES.md](EXAMPLES.md) are the safest starting point.
- This repo now favors tested, honest workflows over feature claims.
