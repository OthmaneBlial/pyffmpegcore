# Deterministic media methodology

The repository does not download mutable third-party media for its core suite.

`tests/media/manifest.json` declares each generated fixture, its `lavfi` or first-party source, license, FFmpeg argument array, expected container/codec properties, duration or dimensions, and validation policy. `tests/media/download_fixtures.py --force` regenerates the corpus from an empty directory.

The corpus covers representative MP4/H.264/AAC, WebM/VP9/Opus, MOV
video-only, MP3, WAV/PCM, PNG, JPEG, and SRT inputs. It also exercises
multiple audio tracks, embedded subtitles, chapters, attached cover art,
display rotation, variable frame rate, and Unicode container/stream metadata.
Capability-dependent behavior is skipped only when the local FFmpeg build
proves the relevant encoder or filter is absent.

Failure contracts cover corrupt inputs, missing encoders and filters,
insufficient disk space, interruption, timeout, temporary-workspace cleanup,
and removal of newly created incomplete outputs.

CI separates evidence:

- fast tests validate parsing, command contracts, errors, and helpers;
- full coverage executes the real media suite with an 80% gate;
- exact-artifact smoke installs one prebuilt wheel on Linux, macOS, and Windows;
- the weekly cold run regenerates all fixtures without a cache.

Generated media is excluded from source and wheel artifacts. Tests and the generation manifest are included in the sdist so its evidence can be inspected and reproduced.
