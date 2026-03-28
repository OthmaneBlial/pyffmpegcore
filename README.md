# PyFFmpegCore

A lightweight Python wrapper around FFmpeg and FFprobe for common media-processing workflows.

[![PyPI version](https://badge.fury.io/py/pyffmpegcore.svg)](https://pypi.org/project/pyffmpegcore/)
[![Python versions](https://img.shields.io/pypi/pyversions/pyffmpegcore.svg)](https://pypi.org/project/pyffmpegcore/)
[![License](https://img.shields.io/pypi/l/pyffmpegcore.svg)](https://pypi.org/project/pyffmpegcore/)

## Current Status

As of March 28, 2026, the repository is validated locally with:

- Python `3.12`
- FFmpeg/FFprobe available on `PATH`
- `102` passing tests
- real-media coverage using internet-backed fixtures downloaded on demand into `tests/media/downloads/`

## What Is Verified

| Area | Verified behavior |
| --- | --- |
| Core media APIs | real `convert`, `resize`, single-pass `compress`, two-pass `compress`, `extract_audio`, `extract_thumbnail`, `adjust_speed`, `generate_waveform`, `FFprobeRunner.probe`, and progress parsing |
| Example workflows | real smoke coverage for `convert_video.py`, `extract_metadata.py`, `compress_with_progress.py`, `extract_thumbnail.py`, `generate_waveform.py` |
| Rich example modules | real end-to-end coverage for concatenation, subtitle handling, audio mixing/normalization, batch image conversion, and speed adjustment |
| Failure handling | missing binaries, bad arguments, invalid codecs, missing audio, invalid timestamps, and broken image inputs return readable failures |

Linux is the reference environment used for the current validation runs. The repo also contains path-handling coverage for spaces and apostrophes in important FFmpeg workflows.

Current caveat:

- Linux is the only environment exercised end to end in local validation so far. Windows-style filter-path escaping is unit-tested, and path-heavy workflows such as concat and burned subtitles are covered with spaces and apostrophes.

## Installation

```bash
pip install pyffmpegcore
```

Requirements:

- `ffmpeg`
- `ffprobe`

Both must be installed and available on `PATH`.

## Quick Start

### Convert a video to MP4

```python
from pyffmpegcore import FFmpegRunner

ffmpeg = FFmpegRunner()
result = ffmpeg.convert(
    "input.avi",
    "output.mp4",
    video_codec="libx264",
    audio_codec="aac",
)

if result.returncode == 0:
    print("Conversion successful!")
```

### Extract metadata

```python
from pyffmpegcore import FFprobeRunner

ffprobe = FFprobeRunner()
metadata = ffprobe.probe("video.mp4")

print(f"Duration: {metadata['duration']:.2f} seconds")
print(f"Resolution: {metadata['video']['width']}x{metadata['video']['height']}")
print(f"Video codec: {metadata['video']['codec']}")
```

### Compress with progress tracking

```python
from pyffmpegcore import FFmpegRunner, FFprobeRunner, ProgressCallback

ffmpeg = FFmpegRunner()
ffprobe = FFprobeRunner()
duration = ffprobe.get_duration("input.mp4")

progress_callback = ProgressCallback(total_duration=duration)
result = ffmpeg.compress(
    "input.mp4",
    "compressed.mp4",
    crf=28,
    progress_callback=progress_callback,
)
```

## API Reference

### FFmpegRunner

- `convert(input_file, output_file, progress_callback=None, audio_only=False, **kwargs)`
- `resize(input_file, output_file, width, height, progress_callback=None, **kwargs)`
- `compress(input_file, output_file, target_size_kb=None, crf=23, two_pass=True, progress_callback=None, **kwargs)`
- `extract_audio(input_file, output_file, progress_callback=None, **kwargs)`
- `extract_thumbnail(input_file, output_file, timestamp="00:00:01", width=320, height=None, quality=2)`
- `adjust_speed(input_file, output_file, speed_factor=1.0, audio_pitch=True)`
- `generate_waveform(input_file, output_file, width=800, height=200, colors="white")`
- `run(args, progress_callback=None)`
- `run_with_progress(args, show_percentage=True)`
- `get_version()`

Common kwargs:

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

### FFprobeRunner

- `probe(input_file)`
- `get_duration(input_file)`
- `get_resolution(input_file)`
- `get_bitrate(input_file)`
- `get_version()`

`probe()` returns a simplified metadata structure built from FFprobe JSON. It is not the raw FFprobe payload; stream tags and niche fields are intentionally trimmed down to common fields.

### ProgressCallback

`ProgressCallback` prints structured progress updates and percentage progress when total duration is known.

## Examples

See [EXAMPLES.md](EXAMPLES.md) for the verified example catalog and the example entry points that are covered by the real-media smoke suite.

## Development

The maintained local workflow is documented in [DEVELOPMENT.md](DEVELOPMENT.md).

Quick setup:

```bash
python -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
```

Validation commands:

```bash
python -m compileall pyffmpegcore tests examples
python -m pytest
python -m build
```

## Notes

- The first real-media test run may download fixture files from the internet.
- Downloaded fixtures are ignored by git and stored under `tests/media/downloads/`.
- The repository now favors documented, proven workflows over feature claims that are not backed by tests yet.
