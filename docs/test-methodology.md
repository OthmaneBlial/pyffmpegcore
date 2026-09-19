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
- exact-artifact smoke installs one prebuilt wheel on Linux, macOS, and Windows,
  then validates four expected refusal codes and their remedies without
  overwriting an existing output;
- the weekly cold run regenerates all fixtures without a cache.
- the bounded [parser mutation corpus](https://github.com/OthmaneBlial/pyffmpegcore/tree/main/fuzz)
  replays valid/invalid pipeline, profile, and receipt documents, then mutates
  them with fixed seeds and preserves unexpected inputs for replay.

Each exact-artifact job uploads its command results and a capability-catalog
report. `scripts/summarize_compatibility.py` rejects missing/failed cells,
unvalidated expected refusals, and mixed wheel hashes before creating the CI
job summary and Markdown artifact.
The dated [compatibility policy](COMPATIBILITY.md) distinguishes those media
checks from Linux-only package contracts and untested OS/Python combinations.

Generated media is excluded from source and wheel artifacts. Tests and the generation manifest are included in the sdist so its evidence can be inspected and reproduced.
