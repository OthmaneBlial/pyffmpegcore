# JSON schemas

Machine-readable outputs are versioned as their contracts stabilize.

## `doctor --json`

The current beta document contains `cli_version`, `platform`, `python`, `ffmpeg`, `ffprobe`, and `capabilities`. Capability keys include counts, selected core encoder/filter availability, and hardware accelerators.

## `probe --json`

The current simplified probe document contains format fields, normalized duration/size/bitrate, stream summaries, first video/audio convenience objects, and chapters when present. It is not yet a lossless representation of all FFprobe data.

## `smoke-test --json`

The document uses `schema_version: "1.0"` and reports status, retention behavior, workspace policy, and probe summaries for the synthetic input and generated thumbnail.

Planned execution plans, receipts, profiles, and pipelines have separate schema files and migration rules. Human terminal output is allowed to evolve; versioned JSON fields follow the documented compatibility and deprecation policy.
