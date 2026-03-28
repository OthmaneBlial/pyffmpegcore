# Release Checklist

Acceptance date: 2026-03-28

## Release Gate

- [x] Fresh media fixtures downloaded into a clean temporary workspace with `tests/media/download_fixtures.py --output-dir /tmp/pyffmpegcore-acceptance-fb_h_f3q/fixtures --force`
- [x] End-to-end acceptance run executed from `/tmp/pyffmpegcore-acceptance-fb_h_f3q/work dir with spaces`
- [x] Full automated test suite passed with `.venv/bin/python -m pytest`
- [x] Distribution artifacts built with `.venv/bin/python -m build`

## Fresh Acceptance Coverage

The final acceptance run used newly downloaded public sample media, not the repository cache, and exercised these verified workflows:

- `examples/convert_video.py`
- `examples/extract_metadata.py`
- `examples/compress_with_progress.py`
- `examples/extract_thumbnail.py`
- `examples/generate_waveform.py`
- `examples/adjust_video_speed.py`
- `examples/concatenate_videos.py`
- `examples/handle_subtitles.py`
- `examples/mix_audio.py`
- `examples/normalize_audio.py`
- `examples/batch_convert_images.py`

Representative outputs were then re-checked with `ffprobe` and decoded with `ffmpeg -v error -i <output> -f null -` to confirm they were readable artifacts.

## Final Validation Results

- `.venv/bin/python -m pytest`: `105 passed in 127.31s`
- `.venv/bin/python -m build`: built `pyffmpegcore-0.1.2.tar.gz` and `pyffmpegcore-0.1.2-py3-none-any.whl`

## Honest Caveats

- The deepest acceptance pass in this session was run on Linux.
- The environment was terminal-only, so true interactive human playback review was not possible here.
- Manual acceptance was approximated with fresh downloads, end-to-end example execution, output probing, and decode checks. If a release requires human sight-and-sound review, that should still be repeated on a workstation with a media player before publishing.
