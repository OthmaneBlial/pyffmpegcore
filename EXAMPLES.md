# PyFFmpegCore Examples

This document provides detailed explanations of all the example scripts included with PyFFmpegCore. Each example demonstrates specific functionality and includes use cases, code explanations, and expected outputs.

## Table of Contents

- [Basic Operations](#basic-operations)
  - [Video Conversion](#video-conversion)
  - [Metadata Extraction](#metadata-extraction)
  - [Progress Tracking](#progress-tracking)
- [Advanced Video Processing](#advanced-video-processing)
  - [Video Concatenation](#video-concatenation)
  - [Video Speed Adjustment](#video-speed-adjustment)
- [Audio Processing](#audio-processing)
  - [Audio Mixing](#audio-mixing)
  - [Audio Normalization](#audio-normalization)
- [Subtitles](#subtitles)
  - [Subtitle Handling](#subtitle-handling)
- [Image Processing](#image-processing)
  - [Batch Image Conversion](#batch-image-conversion)
  - [Thumbnail Extraction](#thumbnail-extraction)
  - [Waveform Generation](#waveform-generation)

## Basic Operations

### Video Conversion

**File:** `examples/convert_video.py`

**Purpose:** Convert video files between different formats and codecs.

**Use Cases:**
- Format conversion (AVI to MP4, MOV to WebM)
- Codec optimization (H.264, H.265, VP9)
- Cross-platform compatibility
- Storage optimization

**Key Features Demonstrated:**
- Basic format conversion
- Codec specification
- Error handling
- Return code checking

**Code Example:**
```python
from pyffmpegcore import FFmpegRunner

ffmpeg = FFmpegRunner()
result = ffmpeg.convert(
    input_file="input.avi",
    output_file="output.mp4",
    video_codec="libx264",
    audio_codec="aac"
)

if result.returncode == 0:
    print("Conversion successful!")
```

**Expected Output:**
```
Conversion successful!
```

### Metadata Extraction

**File:** `examples/extract_metadata.py`

**Purpose:** Extract comprehensive metadata from media files using FFprobe.

**Use Cases:**
- Content analysis and cataloging
- Quality assessment
- Format detection
- Technical specifications gathering
- Automated processing decisions

**Key Features Demonstrated:**
- Full metadata extraction
- Stream-specific information
- Quick access helper methods
- Type-safe data handling

**Code Example:**
```python
from pyffmpegcore import FFprobeRunner

ffprobe = FFprobeRunner()
metadata = ffprobe.probe("sample.mp4")

print(f"Duration: {metadata['duration']:.2f} seconds")
print(f"Resolution: {metadata['video']['width']}x{metadata['video']['height']}")
print(f"Video codec: {metadata['video']['codec']}")

# Quick access methods
duration = ffprobe.get_duration("sample.mp4")
resolution = ffprobe.get_resolution("sample.mp4")
```

**Expected Output:**
```
File Metadata:
Filename: sample.mp4
Format: QuickTime / MOV
Duration: 120.50 seconds
Size: 15728640 bytes
Bitrate: 1048576 bps

Video Stream:
Codec: h264
Resolution: 1920x1080
Duration: 120.50 seconds

Audio Stream:
Codec: aac
Sample Rate: 44100 Hz
Channels: 2

Quick Access:
Duration: 120.50s
Resolution: (1920, 1080)
Bitrate: 1048576 bps
```

### Progress Tracking

**File:** `examples/compress_with_progress.py`

**Purpose:** Monitor encoding progress in real-time during long operations.

**Use Cases:**
- User interface progress bars
- Batch processing monitoring
- Long-running job tracking
- Quality assurance logging
- Resource usage monitoring

**Key Features Demonstrated:**
- Progress callback integration
- Duration-based percentage calculation
- Real-time progress updates
- Structured progress data

**Code Example:**
```python
from pyffmpegcore import FFmpegRunner, FFprobeRunner, ProgressCallback

# Get duration for progress calculation
ffprobe = FFprobeRunner()
duration = ffprobe.get_duration("input.mp4")

# Create progress callback
progress_callback = ProgressCallback(total_duration=duration)

# Compress with progress tracking
ffmpeg = FFmpegRunner()
result = ffmpeg.compress(
    input_file="input.mp4",
    output_file="compressed.mp4",
    crf=28,
    progress_callback=progress_callback
)
```

**Expected Output:**
```
Input duration: 120.50 seconds
50.0% - {'time_seconds': 60.25, 'frame': 1506, 'fps': 25.0, 'status': 'progress'}
100% - Conversion completed!
Compression successful!
```

## Advanced Video Processing

### Video Concatenation

**File:** `examples/concatenate_videos.py`

**Purpose:** Join multiple video files together seamlessly.

**Use Cases:**
- Creating compilation videos
- Combining recorded segments
- Time-lapse sequences
- Multi-part content assembly
- Video editing workflows

**Key Features Demonstrated:**
- Basic stream copying concatenation
- Re-encoding concatenation (handles different codecs)
- Crossfade transitions
- Video information analysis
- Error handling for missing files

**Code Example:**
```python
from pyffmpegcore import FFmpegRunner

def concatenate_videos_basic(video_files: list, output_file: str) -> bool:
    """Fast concatenation using stream copying."""
    runner = FFmpegRunner()

    # Create concat file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for video_file in video_files:
            f.write(f"file '{video_file}'\n")

    args = [
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        "-y", output_file
    ]

    result = runner.run(args)
    return result.returncode == 0
```

**Expected Output:**
```
Found 3 video files to concatenate
✓ Basic concatenation completed
✓ Re-encoding concatenation completed
✓ Transition concatenation completed
```

### Video Speed Adjustment

**File:** `examples/adjust_video_speed.py`

**Purpose:** Change playback speed of videos while optionally maintaining audio pitch.

**Use Cases:**
- Creating time-lapse videos
- Speeding up tutorials or lectures
- Slow motion effects
- Content optimization for different audiences
- Audio tempo adjustment for music

**Key Features Demonstrated:**
- Speed multiplier control
- Audio pitch preservation
- Time-lapse creation
- Slow motion effects
- Video summary creation with highlights
- Reverse video playback

**Code Example:**
```python
from pyffmpegcore import FFmpegRunner

def change_video_speed(video_file: str, output_file: str, speed_multiplier: float,
                      maintain_audio_pitch: bool = True) -> bool:
    """Change video playback speed."""
    runner = FFmpegRunner()

    # Video speed adjustment (setpts)
    video_speed = 1.0 / speed_multiplier

    # Audio speed adjustment
    if maintain_audio_pitch:
        audio_filter = f"atempo={speed_multiplier}"
    else:
        audio_filter = f"asetrate=44100*{speed_multiplier},aresample=44100"

    args = [
        "-i", video_file,
        "-filter_complex", f"[0:v]setpts={video_speed}*PTS[v];[0:a]{audio_filter}[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-y", output_file
    ]

    result = runner.run(args)
    return result.returncode == 0
```

**Expected Output:**
```
Video speed adjusted (2x): sped_up_2x.mp4
✓ Video sped up 2x with maintained pitch
✓ Slow motion video created
✓ Time-lapse video created
✓ Video reversed
✓ Video summary created
```

## Audio Processing

### Audio Mixing

**File:** `examples/mix_audio.py`

**Purpose:** Combine multiple audio files through mixing or sequential merging.

**Use Cases:**
- Creating music mashups
- Audio post-production
- Podcast editing
- Sound design
- Background music mixing

**Key Features Demonstrated:**
- Simultaneous audio mixing with volume control
- Sequential audio concatenation
- Crossfade transitions
- Stereo creation from mono files
- Background music addition
- Audio information analysis

**Code Example:**
```python
from pyffmpegcore import FFmpegRunner

def mix_audio_files(audio_files: list, output_file: str, volumes: list = None) -> bool:
    """Mix multiple audio files with optional volume control."""
    runner = FFmpegRunner()

    # Build input arguments
    args = []
    for audio_file in audio_files:
        args.extend(["-i", audio_file])

    # Build filter complex for mixing
    filter_parts = []
    for i, audio_file in enumerate(audio_files):
        if volumes and volumes[i] != 1.0:
            filter_parts.append(f"[{i}:a]volume={volumes[i]}[a{i}];")
        else:
            filter_parts.append(f"[{i}:a][a{i}];")

    # Mix all audio streams
    mix_inputs = "".join([f"[a{i}]" for i in range(len(audio_files))])
    filter_parts.append(f"{mix_inputs}amix=inputs={len(audio_files)}:duration=longest[aout]")

    filter_complex = "".join(filter_parts)

    args.extend([
        "-filter_complex", filter_complex,
        "-map", "[aout]",
        "-c:a", "aac",
        "-b:a", "192k",
        "-y", output_file
    ])

    result = runner.run(args)
    return result.returncode == 0
```

**Expected Output:**
```
Found 3 audio files to mix
✓ Audio mixing completed
✓ Sequential merging completed
✓ Audio mashup completed
✓ Background music added
```

### Audio Normalization

**File:** `examples/normalize_audio.py`

**Purpose:** Apply professional audio normalization and dynamic range processing.

**Use Cases:**
- Consistent audio levels across tracks
- Podcast production
- Music mastering
- Broadcasting standards compliance
- Audio post-production

**Key Features Demonstrated:**
- EBU R128 loudness normalization
- Peak level normalization
- Dynamic range compression
- Brickwall limiting
- Complete mastering chains
- Batch processing

**Code Example:**
```python
from pyffmpegcore import FFmpegRunner

def normalize_audio_loudnorm(audio_file: str, output_file: str,
                           target_i: float = -16.0) -> bool:
    """Normalize audio using EBU R128 standard."""
    runner = FFmpegRunner()

    loudnorm_filter = f"loudnorm=I={target_i}:TP=-1.5:LRA=11"

    args = [
        "-i", audio_file,
        "-af", loudnorm_filter,
        "-c:a", "aac",
        "-b:a", "192k",
        "-y", output_file
    ]

    result = runner.run(args)
    return result.returncode == 0

def apply_compression(audio_file: str, output_file: str,
                     threshold: float = -20.0, ratio: float = 4.0) -> bool:
    """Apply dynamic range compression."""
    runner = FFmpegRunner()

    compand_filter = f"compand=attacks=0.0001:decays=0.2:points=-70/-70|-60/-20|{threshold}/{threshold}|20/20"

    args = [
        "-i", audio_file,
        "-af", compand_filter,
        "-c:a", "aac",
        "-b:a", "192k",
        "-y", output_file
    ]

    result = runner.run(args)
    return result.returncode == 0
```

**Expected Output:**
```
Duration: 180.50s
Sample Rate: 44100 Hz
Channels: 2
Codec: aac

✓ EBU R128 normalization applied
✓ Peak level normalized to -3dB
✓ Compression applied
✓ Limiter applied
✓ Full mastering chain applied
```

## Subtitles

### Subtitle Handling

**File:** `examples/handle_subtitles.py`

**Purpose:** Extract, burn, and manipulate subtitles in video files.

**Use Cases:**
- Adding subtitles to videos for accessibility
- Extracting subtitles for translation
- Burning subtitles permanently into video
- Converting between subtitle formats
- Multi-language subtitle support

**Key Features Demonstrated:**
- Subtitle stream extraction
- Hard subtitle burning
- Subtitle track addition
- Format conversion
- Multi-language support
- Subtitle stream detection

**Code Example:**
```python
from pyffmpegcore import FFmpegRunner

def burn_subtitles(video_file: str, subtitle_file: str, output_file: str,
                  font_size: int = 24, font_color: str = "white") -> bool:
    """Burn subtitles permanently into a video file."""
    runner = FFmpegRunner()

    subtitle_filter = f"subtitles='{subtitle_file}':force_style='FontSize={font_size},PrimaryColour=&H{font_color}'"

    args = [
        "-i", video_file,
        "-vf", subtitle_filter,
        "-c:a", "copy",
        "-y", output_file
    ]

    result = runner.run(args)
    return result.returncode == 0

def add_subtitle_track(video_file: str, subtitle_file: str, output_file: str,
                      language: str = "eng") -> bool:
    """Add subtitles as a separate track."""
    runner = FFmpegRunner()

    args = [
        "-i", video_file,
        "-i", subtitle_file,
        "-c:v", "copy",
        "-c:a", "copy",
        "-c:s", "mov_text",
        "-metadata:s:s:0", f"language={language}",
        "-y", output_file
    ]

    result = runner.run(args)
    return result.returncode == 0
```

**Expected Output:**
```
Stream 0: mov_text (eng) -
✓ Subtitles extracted
✓ Subtitles burned into video
✓ Subtitle track added
✓ Subtitles converted to VTT format
✓ Multi-language subtitles added
```

## Image Processing

### Batch Image Conversion

**File:** `examples/batch_convert_images.py`

**Purpose:** Convert multiple images between formats with optimization.

**Use Cases:**
- Web optimization (PNG to JPEG/WebP)
- Storage format conversion
- Batch processing workflows
- Image format standardization
- Quality and size optimization

**Key Features Demonstrated:**
- Format conversion (PNG, JPEG, WebP)
- Quality control
- Resizing with aspect ratio preservation
- Batch processing
- Web optimization
- Progress tracking

**Code Example:**
```python
from pyffmpegcore import FFmpegRunner

def convert_image(input_path: str, output_path: str, quality: int = 80,
                 resize: Tuple[int, int] = None, **kwargs) -> bool:
    """Convert a single image to a different format."""
    ffmpeg = FFmpegRunner()

    args = ["-i", input_path]

    # Build video filter chain
    vf_filters = []
    if resize:
        width, height = resize
        vf_filters.append(f"scale={width}:{height}")

    if vf_filters:
        args.extend(["-vf", ",".join(vf_filters)])

    # Set quality based on output format
    output_ext = os.path.splitext(output_path)[1].lower()
    if output_ext in ['.jpg', '.jpeg']:
        args.extend(["-q:v", str(min(31, max(1, 31 - int(quality * 31 / 100))))])
    elif output_ext in ['.webp']:
        args.extend(["-quality", str(quality)])

    # Additional FFmpeg options
    for key, value in kwargs.items():
        if key.startswith('ffmpeg_'):
            args.extend([f"-{key[7:]}", str(value)])

    args.extend(["-y", output_path])

    result = ffmpeg.run(args)
    return result.returncode == 0
```

**Expected Output:**
```
Converting to WebP format...
Found 5 images to convert
✓ Converted: image1.jpg
✓ Converted: image2.png
✓ Converted: image3.tiff
✓ Converted: image4.bmp
✓ Converted: image5.gif
```

### Thumbnail Extraction

**File:** `examples/extract_thumbnail.py`

**Purpose:** Extract thumbnails and preview images from video files.

**Use Cases:**
- Video preview generation
- Content management systems
- Social media previews
- Video gallery thumbnails
- Quality control and review

**Key Features Demonstrated:**
- Single thumbnail extraction
- Multiple thumbnail generation
- Smart thumbnail selection
- Custom timestamp selection
- Batch processing
- Quality control

**Code Example:**
```python
from pyffmpegcore import FFmpegRunner

def extract_thumbnail(video_file: str, output_file: str, timestamp: str = "00:00:01") -> bool:
    """Extract a single thumbnail from a video."""
    runner = FFmpegRunner()

    args = [
        "-i", video_file,
        "-ss", timestamp,  # Seek to timestamp
        "-vframes", "1",   # Extract one frame
        "-q:v", "2",       # High quality
        "-y", output_file
    ]

    result = runner.run(args)
    return result.returncode == 0

def extract_multiple_thumbnails(video_file: str, output_pattern: str, count: int = 10) -> bool:
    """Extract multiple thumbnails evenly spaced throughout the video."""
    runner = FFmpegRunner()
    ffprobe = FFprobeRunner()

    # Get video duration
    metadata = ffprobe.probe(video_file)
    duration = metadata.get("duration", 0)

    if duration == 0:
        return False

    # Calculate timestamps
    interval = duration / (count + 1)

    for i in range(count):
        timestamp = (i + 1) * interval
        hours = int(timestamp // 3600)
        minutes = int((timestamp % 3600) // 60)
        seconds = int(timestamp % 60)

        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        output_file = output_pattern.format(i=i+1)

        args = [
            "-i", video_file,
            "-ss", time_str,
            "-vframes", "1",
            "-q:v", "2",
            "-y", output_file
        ]

        result = runner.run(args)
        if result.returncode != 0:
            return False

    return True
```

**Expected Output:**
```
✓ Extracted thumbnail at 00:00:01
✓ Extracted 10 thumbnails
✓ Extracted smart thumbnails based on scene changes
```

### Waveform Generation

**File:** `examples/generate_waveform.py`

**Purpose:** Generate audio waveform visualizations and spectrograms.

**Use Cases:**
- Audio content preview
- Podcast thumbnails
- Music visualization
- Audio editing interfaces
- Content analysis

**Key Features Demonstrated:**
- Waveform image generation
- Detailed waveform analysis
- Animated waveform sequences
- Metadata overlay
- Custom styling options

**Code Example:**
```python
from pyffmpegcore import FFmpegRunner

def generate_waveform_image(audio_file: str, output_file: str,
                          width: int = 800, height: int = 200) -> bool:
    """Generate a static waveform image."""
    runner = FFmpegRunner()

    filter_complex = (
        f"[0:a]aformat=channel_layouts=mono,"
        f"showwavespic=s={width}x{height}:colors=white[waveform];"
        f"color=black:s={width}x{height}[bg];"
        f"[bg][waveform]overlay=format=auto"
    )

    args = [
        "-i", audio_file,
        "-filter_complex", filter_complex,
        "-vframes", "1",
        "-y", output_file
    ]

    result = runner.run(args)
    return result.returncode == 0

def generate_detailed_waveform(audio_file: str, output_file: str) -> bool:
    """Generate a detailed waveform with multiple visualizations."""
    runner = FFmpegRunner()

    filter_complex = (
        # Split audio into channels
        "[0:a]asplit=3[chan1][chan2][chan3];"
        # Left channel waveform
        "[chan1]showwaves=mode=line:s=800x100:colors=blue[waveL];"
        # Right channel waveform
        "[chan2]showwaves=mode=line:s=800x100:colors=red[waveR];"
        # Spectrogram
        "[chan3]showspectrumpic=s=800x200:legend=1[spectrogram];"
        # Combine vertically
        "[waveL][waveR]vstack[channels];"
        "[channels][spectrogram]vstack[final]"
    )

    args = [
        "-i", audio_file,
        "-filter_complex", filter_complex,
        "-map", "[final]",
        "-y", output_file
    ]

    result = runner.run(args)
    return result.returncode == 0
```

**Expected Output:**
```
✓ Generated waveform image
✓ Generated detailed waveform with spectrogram
✓ Generated animated waveform sequence
✓ Generated waveform with metadata overlay
```

## Running the Examples

To run any of these examples:

1. Ensure FFmpeg and FFprobe are installed and in your PATH
2. Install PyFFmpegCore: `pip install pyffmpegcore`
3. Navigate to the examples directory
4. Run the desired example: `python convert_video.py`

Note: Most examples use placeholder filenames. Replace these with actual media files on your system, or modify the examples to use your test files.

## Common Patterns

Across all examples, you'll see these common patterns:

- **Error Handling**: Always check `result.returncode == 0`
- **Progress Tracking**: Use `ProgressCallback` for long operations
- **Metadata First**: Use FFprobe to gather information before processing
- **Filter Complex**: Advanced operations use FFmpeg's filter system
- **Stream Mapping**: Explicit `-map` options for multi-input operations

## Performance Considerations

- Use hardware acceleration when available (`-hwaccel`)
- Stream copy (`-c copy`) for fast operations when possible
- Two-pass encoding for better quality at target file sizes
- Batch processing for efficiency
- Progress callbacks for user feedback during long operations

For more advanced usage and API details, see the main [README.md](README.md).

## Author

**Othmane BLIAL**