# PyFFmpegCore Examples

This file lists the example scripts that are currently backed by tests in this repository.

## Verified Example Catalog

| Example | Verified entry points | Real-media coverage |
| --- | --- | --- |
| `examples/convert_video.py` | `main()` | converts a real downloaded video into MP4 |
| `examples/extract_metadata.py` | `main()` | probes a real MP4 and prints expected metadata fields |
| `examples/compress_with_progress.py` | `main()` | compresses a real MP4 while emitting progress updates |
| `examples/extract_thumbnail.py` | `extract_thumbnail()`, `extract_multiple_thumbnails()`, `extract_smart_thumbnails()` | generates real thumbnail files from a downloaded video |
| `examples/generate_waveform.py` | `generate_waveform_image()`, `generate_detailed_waveform()`, `generate_waveform_animation()`, `generate_waveform_with_metadata()` | creates real waveform images/video from downloaded audio |
| `examples/concatenate_videos.py` | `concatenate_videos_basic()`, `concatenate_videos_reencode()` | validates stream-copy concat, re-encode concat, durations, and special-character paths |
| `examples/handle_subtitles.py` | `add_subtitle_track()`, `extract_subtitles()`, `burn_subtitles()` | validates subtitle muxing, extraction, and burned subtitle output on real media |
| `examples/mix_audio.py` | `mix_audio_files()`, `merge_audio_sequentially()`, `create_audio_mashup()`, `add_background_music()` | validates mixing, sequential merge, mashup, and background-music workflows |
| `examples/normalize_audio.py` | `normalize_audio_loudnorm()`, `create_mastered_audio()` | validates loudness changes and playable mastered output |
| `examples/batch_convert_images.py` | `convert_image()`, `batch_convert_images()`, `optimize_images_for_web()`, `convert_to_webp_batch()` | validates PNG/JPG/WebP conversion and broken-file reporting |
| `examples/adjust_video_speed.py` | key helper functions plus real output checks | validates faster/slower outputs on real media |

## Demonstration-Only Notes

Some `main()` functions in the larger example modules are illustrative rather than fixture-aware. They may use placeholder filenames, directories, or timestamps that assume you replace them with your own media.

The verified, tested entry points are the ones listed in the table above.

## Running The Examples Locally

Set up a local environment:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

Make sure `ffmpeg` and `ffprobe` are available:

```bash
ffmpeg -version
ffprobe -version
```

Download the fixture corpus used by the real-media tests:

```bash
python tests/media/download_fixtures.py
```

Run the example smoke coverage:

```bash
python -m pytest tests/examples/test_examples_smoke_real.py
```

Run the full example-related coverage:

```bash
python -m pytest tests/examples
```

## Current Scope

The examples are now treated as part of the public contract of the repository. If an example cannot be exercised honestly against real media, it should either be rewritten to match real behavior or reduced to clearly labeled demonstration code.
