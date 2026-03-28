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
