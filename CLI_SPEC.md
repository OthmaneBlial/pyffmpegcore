# PyFFmpegCore CLI Specification

## Purpose

This document defines the public command-line surface for the first real PyFFmpegCore CLI release.

The CLI is meant to make the repository's already-verified media workflows available directly from the terminal without requiring users to write Python code.

## Product Positioning

PyFFmpegCore CLI is:

- a task-focused wrapper around `ffmpeg` and `ffprobe`
- aimed at normal terminal users, not only Python developers
- built around proven workflows already validated in this repository

PyFFmpegCore CLI is not:

- a full replacement for raw FFmpeg
- a graphical desktop application
- a promise that every obscure codec or filter combination will be abstracted

## Version 1 Goals

Version `1` of the CLI should let users do the most common, already-proven jobs directly:

- inspect a file
- convert media
- compress video
- extract audio
- create thumbnails
- generate waveforms
- change speed
- concatenate clips
- work with subtitles
- mix and normalize audio
- batch-process images
- diagnose the local FFmpeg environment

## Version 1 Public Commands

The first CLI release should expose these top-level commands:

- `doctor`
- `probe`
- `convert`
- `compress`
- `extract-audio`
- `thumbnail`
- `waveform`
- `speed`
- `concat`
- `subtitles`
- `mix-audio`
- `normalize-audio`
- `images`

## Command Tree

The CLI should keep simple one-shot jobs flat, and use subcommands only where they reduce ambiguity.

### Flat Commands

- `pyffmpegcore doctor`
- `pyffmpegcore probe`
- `pyffmpegcore convert`
- `pyffmpegcore compress`
- `pyffmpegcore extract-audio`
- `pyffmpegcore thumbnail`
- `pyffmpegcore waveform`
- `pyffmpegcore concat`
- `pyffmpegcore normalize-audio`

### Grouped Commands

- `pyffmpegcore speed video`
- `pyffmpegcore speed audio`
- `pyffmpegcore subtitles add`
- `pyffmpegcore subtitles extract`
- `pyffmpegcore subtitles burn`
- `pyffmpegcore mix-audio mix`
- `pyffmpegcore mix-audio concat`
- `pyffmpegcore mix-audio mashup`
- `pyffmpegcore mix-audio background`
- `pyffmpegcore images convert`
- `pyffmpegcore images optimize`
- `pyffmpegcore images webp`

## Naming Rules

- Use verbs that match user intent, such as `extract-audio` instead of internal method names.
- Use grouped commands when the same noun has clearly different operations, such as `subtitles add` versus `subtitles burn`.
- Avoid exposing raw FFmpeg vocabulary unless users are likely to search for it directly.

## Planned Input Model

The CLI should prefer named arguments for important file paths:

- `--input`
- `--output`
- `--input-dir`
- `--output-dir`

For commands that naturally take multiple source files, the CLI should use either:

- repeated positional inputs for clip lists, or
- an explicit multi-value flag such as `--inputs`

Version `1` should bias toward explicit file arguments over implicit file discovery.

## Parser And Framework Decision

Version `1` should use the Python standard library `argparse` module.

Reasons for this choice:

- no extra runtime dependency is required
- packaging stays simple
- help output is good enough for a first serious CLI release
- it is easy to test with both direct function calls and subprocess calls
- it avoids introducing framework-specific behavior before the command set stabilizes

Higher-level frameworks can be reconsidered later only if they solve a real user problem that `argparse` is making harder.

## Parser Conventions

- Global options should include `--verbose`, `--quiet`, `--ffmpeg-path`, and `--ffprobe-path`.
- Required file paths should use explicit names rather than positional guessing where readability matters.
- Commands that write files should require an explicit output target unless a later phase defines a safe default.
- Help text should show at least one short example for user-facing commands.
- The CLI should return numeric exit codes instead of relying only on exception text.

## Example Command Shapes

These examples describe the intended UX shape:

```bash
pyffmpegcore probe --input holiday.mp4
pyffmpegcore convert --input clip.webm --output clip.mp4
pyffmpegcore compress --input upload.mp4 --output upload-small.mp4 --crf 28
pyffmpegcore extract-audio --input interview.mp4 --output interview.mp3
pyffmpegcore speed video --input demo.mp4 --output demo-fast.mp4 --factor 1.5
pyffmpegcore subtitles burn --video lesson.mp4 --subtitle english.srt --output lesson-burned.mp4
pyffmpegcore mix-audio background --main-input voice.wav --background-input music.mp3 --output episode.mp3
pyffmpegcore images webp --input-dir photos --output-dir photos-webp
```

## Version 1 Non-Goals

The first CLI release should not try to do all of the following:

- expose every FFmpeg flag one-to-one
- bundle FFmpeg itself inside the Python package
- auto-detect perfect settings for every media file
- pretend Linux, macOS, and Windows can all share the same installer story
- add new media-processing features that the repository does not already prove

## User Experience Rules

- Commands should read like tasks, not internal implementation details.
- Output should be understandable without FFmpeg expertise.
- Required input files should be explicit.
- Output files should never be overwritten silently.
- Errors should tell the user what went wrong and what to fix next.

## Release Bar

- Every public CLI command must have help text and at least one usage example.
- Every public CLI command must be backed by automated tests before release.
- The first release should prefer a small clean command surface over a large confusing one.
