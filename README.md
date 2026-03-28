# PyFFmpegCore

A terminal-first media toolkit built on top of `ffmpeg` and `ffprobe`.

Use it when you want to:

- inspect a video or audio file
- convert video formats
- compress large videos
- extract audio from video
- grab thumbnails
- generate waveform images
- join clips together
- add, extract, or burn subtitles
- mix or normalize audio
- batch-convert images

[![PyPI version](https://badge.fury.io/py/pyffmpegcore.svg)](https://pypi.org/project/pyffmpegcore/)
[![Python versions](https://img.shields.io/pypi/pyversions/pyffmpegcore.svg)](https://pypi.org/project/pyffmpegcore/)
[![License](https://img.shields.io/pypi/l/pyffmpegcore.svg)](https://pypi.org/project/pyffmpegcore/)

## What This Project Is

PyFFmpegCore is now designed to be used first as a CLI:

```bash
pyffmpegcore ...
```

It also still exposes a Python API for developers, but the easiest way to use the project is now the terminal command.

## What Is Verified

As of March 28, 2026, the repo was validated locally with:

- Python `3.12`
- `ffmpeg` and `ffprobe` available on `PATH`
- `105` library and CLI tests
- real downloaded video, audio, subtitle, and image fixtures
- end-to-end CLI checks for the shipped commands
- path handling for spaces and apostrophes in important workflows

The strongest validation was done on Linux. The repo also now includes installer, packaging, and clean-install checks for the CLI path.

## Install

You need:

- Python `3.8+`
- `ffmpeg`
- `ffprobe`

Install the CLI with `pipx`:

```bash
pipx install pyffmpegcore
```

Or with regular `pip`:

```bash
python -m pip install --user pyffmpegcore
```

From a repo checkout you can also use the one-command installers:

```bash
./install.sh
```

Windows uses the PowerShell installer instead:

```powershell
.\install.ps1
```

Then confirm the install:

```bash
pyffmpegcore --version
pyffmpegcore doctor
```

More install details are in [CLI_INSTALL.md](CLI_INSTALL.md).

## Five-Minute Start

If you already have your own files, replace the sample names below with your own.

### 1. Check your setup

```bash
pyffmpegcore doctor
```

### 2. Inspect a file before changing it

```bash
pyffmpegcore probe --input my-video.mp4
```

### 3. Convert a WebM or MOV into MP4

```bash
pyffmpegcore convert --input input.webm --output output.mp4 --video-codec libx264 --audio-codec aac
```

### 4. Make a large video smaller

```bash
pyffmpegcore compress --input large-video.mp4 --output smaller-video.mp4 --crf 28
```

### 5. Pull the audio out of a video

```bash
pyffmpegcore extract-audio --input interview.mp4 --output interview.mp3
```

## Practice With The Same Real Files Used In Tests

If you want safe practice files instead of your own media, download the same fixtures used in real validation:

```bash
python tests/media/download_fixtures.py
```

That creates files under `tests/media/downloads/`.

Main practice files:

| File | What it represents |
| --- | --- |
| `tests/media/downloads/sample_mp4_h264.mp4` | a normal MP4 clip with video and audio |
| `tests/media/downloads/sample_webm_vp9.webm` | a WebM video you want to convert |
| `tests/media/downloads/sample_video_mov.mov` | a camera or editor export |
| `tests/media/downloads/sample_audio_mp3.mp3` | a song, podcast, or voice-over clip |
| `tests/media/downloads/sample_audio_wav.wav` | an uncompressed audio recording |
| `tests/media/downloads/sample_image_png.png` | a graphic or screenshot |
| `tests/media/downloads/sample_image_jpg.jpg` | a photo |
| `tests/media/downloads/sample_subtitles.srt` | a subtitle file you want to attach or burn |

## Copy-Paste Commands

### Inspect a file

```bash
pyffmpegcore probe --input tests/media/downloads/sample_mp4_h264.mp4
pyffmpegcore probe --input tests/media/downloads/sample_mp4_h264.mp4 --json
```

### Convert WebM to MP4

```bash
pyffmpegcore convert \
  --input tests/media/downloads/sample_webm_vp9.webm \
  --output converted.mp4 \
  --video-codec libx264 \
  --audio-codec aac
```

### Compress a video

```bash
pyffmpegcore compress \
  --input tests/media/downloads/sample_mp4_h264.mp4 \
  --output compressed.mp4 \
  --crf 28
```

### Extract audio

```bash
pyffmpegcore extract-audio \
  --input tests/media/downloads/sample_mp4_h264.mp4 \
  --output audio-only.mp3
```

### Create a thumbnail

```bash
pyffmpegcore thumbnail \
  --input tests/media/downloads/sample_mp4_h264.mp4 \
  --output thumbnail.jpg \
  --timestamp 00:00:01 \
  --width 640
```

### Generate a waveform image

```bash
pyffmpegcore waveform \
  --input tests/media/downloads/sample_audio_mp3.mp3 \
  --output waveform.png \
  --width 1200 \
  --height 300
```

### Burn subtitles into a video

```bash
pyffmpegcore subtitles burn \
  --video tests/media/downloads/sample_mp4_h264.mp4 \
  --subtitle tests/media/downloads/sample_subtitles.srt \
  --output burned-subtitles.mp4
```

### Join matching clips together

```bash
pyffmpegcore concat \
  --inputs tests/media/downloads/sample_mp4_h264.mp4 tests/media/downloads/sample_mp4_h264.mp4 \
  --output joined.mp4 \
  --mode copy
```

## Use Your Own Files

Replace the sample paths with your own real filenames:

- `tests/media/downloads/sample_webm_vp9.webm` -> `holiday-video.webm`
- `tests/media/downloads/sample_mp4_h264.mp4` -> `screen-recording.mp4`
- `tests/media/downloads/sample_audio_mp3.mp3` -> `podcast-intro.mp3`
- `tests/media/downloads/sample_subtitles.srt` -> `captions/english.srt`

Good habits:

- put quotes around paths that contain spaces
- choose the output extension you actually want, like `.mp4`, `.mp3`, `.wav`, `.jpg`, or `.webp`
- use `pyffmpegcore probe --input your-file` first if you are not sure what kind of file you have
- open the output file in your normal media player after each command

## Help And Shell Completion

Built-in help:

```bash
pyffmpegcore --help
pyffmpegcore convert --help
pyffmpegcore subtitles --help
```

Shell completion:

```bash
pyffmpegcore completion bash
pyffmpegcore completion zsh
pyffmpegcore completion powershell
```

The quick command guide is in [CLI_HELP.md](CLI_HELP.md). More task-based examples are in [EXAMPLES.md](EXAMPLES.md).

## Python API

If you want to call the project from Python code instead of the CLI:

```bash
python -m pip install pyffmpegcore
```

Example:

```python
from pyffmpegcore import FFmpegRunner

ffmpeg = FFmpegRunner()
result = ffmpeg.extract_audio("video.mp4", "audio.mp3")

print(result.returncode)
```

The Python API remains useful, but the supported public path is now the `pyffmpegcore` terminal command first.
