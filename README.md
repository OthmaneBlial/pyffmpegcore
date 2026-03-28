# PyFFmpegCore

A lightweight Python wrapper around FFmpeg/FFprobe for common video/audio processing tasks.

[![PyPI version](https://badge.fury.io/py/pyffmpegcore.svg)](https://pypi.org/project/pyffmpegcore/)
[![Python versions](https://img.shields.io/pypi/pyversions/pyffmpegcore.svg)](https://pypi.org/project/pyffmpegcore/)
[![License](https://img.shields.io/pypi/l/pyffmpegcore.svg)](https://pypi.org/project/pyffmpegcore/)

## Features

- **Simple API**: Convert videos, extract metadata, and track progress in just a few lines of code
- **Lightweight**: The library uses only Python's standard library (no runtime dependencies). Examples use stdlib modules like `concurrent.futures`.
- **Cross-platform**: Works on Linux, macOS, and Windows with FFmpeg installed
- **Progress tracking**: Real-time progress updates during encoding using robust `-progress pipe:1`
- **Two-pass encoding**: Accurate file size targeting for compression
- **Smart defaults**: Automatic pixel format and fast start flags for web compatibility

## Installation

```bash
pip install pyffmpegcore
```

**Requirements**: FFmpeg and FFprobe must be installed and available in your PATH.

## Quick Start

### Convert a video to MP4

```python
from pyffmpegcore import FFmpegRunner

ffmpeg = FFmpegRunner()
result = ffmpeg.convert("input.avi", "output.mp4", video_codec="libx264", audio_codec="aac")

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

# Compress with CRF (quality-based)
ffmpeg = FFmpegRunner()
result = ffmpeg.compress("input.mp4", "compressed.mp4", crf=28)

# Or compress to target file size (two-pass encoding)
result = ffmpeg.compress("input.mp4", "compressed.mp4", target_size_kb=10240)  # ~10MB

# Two-pass with progress tracking
progress_callback = ProgressCallback()
result = ffmpeg.compress("input.mp4", "compressed.mp4", target_size_kb=10240, progress_callback=progress_callback)

# With progress tracking (CRF mode)
result = ffmpeg.compress("input.mp4", "compressed.mp4", crf=28, progress_callback=progress_callback)
```

## API Reference

### FFmpegRunner

Main class for running FFmpeg commands.

#### Methods

- `convert(input_file, output_file, progress_callback=None, audio_only=False, **kwargs)`: Convert between formats
- `resize(input_file, output_file, width, height, progress_callback=None, **kwargs)`: Resize video
- `compress(input_file, output_file, target_size_kb=None, crf=23, two_pass=True, progress_callback=None, **kwargs)`: Compress video
- `extract_audio(input_file, output_file, progress_callback=None, **kwargs)`: Extract audio track
- `extract_thumbnail(input_file, output_file, timestamp="00:00:01", width=320, height=None, quality=2)`: Extract a single frame
- `adjust_speed(input_file, output_file, speed_factor=1.0, audio_pitch=True)`: Change playback speed
- `generate_waveform(input_file, output_file, width=800, height=200, colors="white")`: Generate a waveform image
- `run(args, progress_callback=None)`: Run custom FFmpeg command
- `run_with_progress(args, show_percentage=True)`: Run custom FFmpeg command with console progress output
- `get_version()`: Return the FFmpeg version banner

#### Common kwargs

- `video_codec`: Video codec (e.g., "libx264", "libx265")
- `audio_codec`: Audio codec (e.g., "aac", "libmp3lame", "copy")
- `video_bitrate`: Video bitrate (e.g., "1000k")
- `audio_bitrate`: Audio bitrate (e.g., "128k")
- `preset`: Encoding speed vs compression (e.g., "ultrafast", "medium", "slow")
- `pix_fmt`: Pixel format for encoded video outputs
- `threads`: FFmpeg thread count override
- `movflags`: MP4/M4V muxer flags. Defaults to `+faststart`; set `movflags=None` to disable
- `sample_rate`: Output audio sample rate for `extract_audio`
- `channels`: Output audio channel count for `extract_audio`

#### Automatic features

- **Pixel format**: Automatically sets `yuv420p` for video compatibility (override with `pix_fmt` parameter)
- **Fast start**: Adds `movflags=+faststart` for MP4 files to enable web streaming (set `movflags=None` to disable)
- **Progress tracking**: Uses robust `-progress pipe:1` for reliable progress updates when callback provided
- **Two-pass encoding**: Automatically used when `target_size_kb` is specified

## Windows Notes

- **Path quoting in concat files**: When using `concatenate_videos_basic`, ensure file paths in the concat file are properly escaped. Use forward slashes or double backslashes.
- **Subtitles path escaping**: For `burn_subtitles`, paths with backslashes need escaping (e.g., `C:\\path\\to\\subs.srt`).
- **Filter complex quoting**: Complex filter strings may require careful quoting. Use double quotes for paths and single quotes for filter parameters.

### FFprobeRunner

Class for extracting metadata using FFprobe.

#### Methods

- `probe(input_file)`: Get a simplified metadata dictionary
- `get_duration(input_file)`: Get duration in seconds
- `get_resolution(input_file)`: Get video resolution as (width, height)
- `get_bitrate(input_file)`: Get bitrate in bps
- `get_version()`: Return the FFprobe version banner

#### Metadata Structure

`probe()` returns a simplified structure built from FFprobe JSON. The `streams`
list is not the raw FFprobe payload; it contains the most commonly used fields
only.

```python
{
    "filename": "video.mp4",
    "format_name": "mp4",
    "format_long_name": "QuickTime / MOV",
    "duration": 120.5,
    "size": 15728640,
    "bit_rate": 1048576,
    "video": {
        "codec": "h264",
        "width": 1920,
        "height": 1080,
        "duration": 120.5,
        "bit_rate": 1000000
    },
    "audio": {
        "codec": "aac",
        "sample_rate": 44100,
        "channels": 2,
        "bit_rate": 128000
    },
    "streams": [...],  # Simplified per-stream dictionaries
    "chapters": [...]  # Chapter information
}
```

### Progress Tracking

#### ProgressCallback

Helper class for progress callbacks.

```python
from pyffmpegcore import ProgressCallback

# For percentage-based progress
progress = ProgressCallback(total_duration=120.5)  # 120.5 seconds

# Use with FFmpegRunner
ffmpeg.run(args, progress_callback=progress)
```

#### Custom Callbacks

```python
def my_progress_callback(progress_dict):
    if progress_dict.get("status") == "end":
        print("Done!")
    else:
        frame = progress_dict.get("frame", 0)
        fps = progress_dict.get("fps", 0)
        print(f"Frame: {frame}, FPS: {fps}")

ffmpeg.run(args, progress_callback=my_progress_callback)
```

#### Progress Dictionary

```python
{
    "frame": 123,
    "fps": 25.0,
    "size_kb": 5120.5,
    "time_seconds": 4.92,
    "bitrate_kbps": 834.2,
    "speed": 1.25,
    "status": "progress"  # or "end"
}
```

## Examples

See the [`EXAMPLES.md`](EXAMPLES.md) file for detailed explanations of all example scripts, including use cases, code explanations, and expected outputs.

See the `examples/` directory for complete working examples:

### Basic Usage
- `convert_video.py`: Basic video conversion
- `extract_metadata.py`: Metadata extraction
- `compress_with_progress.py`: Compression with progress tracking

### Real-World Applications
- `extract_thumbnail.py`: Extract thumbnails from videos for previews
- `generate_waveform.py`: Generate audio waveform visualizations
- `batch_convert_images.py`: Batch convert images for storage optimization
- `concatenate_videos.py`: Join multiple video files together
- `mix_audio.py`: Mix and merge multiple audio files
- `handle_subtitles.py`: Extract, burn, and manipulate subtitles
- `adjust_video_speed.py`: Change video/audio playback speed
- `normalize_audio.py`: Audio normalization and dynamic range compression

## Development

The maintained local workflow is documented in [DEVELOPMENT.md](DEVELOPMENT.md).

### Quick Setup

```bash
git clone https://github.com/pyffmpegcore/pyffmpegcore.git
cd pyffmpegcore
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

### Testing

```bash
python -m pytest
```

### Building

```bash
python -m build
```

## Author

**Othmane BLIAL**

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## License

MIT License - see LICENSE file for details.

## Requirements

- Python 3.8+
- FFmpeg (with ffprobe) installed and in PATH

### Installing FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.
