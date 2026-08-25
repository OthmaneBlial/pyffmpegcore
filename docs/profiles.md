# Versioned workflow profiles

Profiles are small, reviewable sets of maintained choices. They are not raw command strings and never contain shell fragments.

```bash
pyffmpegcore profile list
pyffmpegcore profile show web/mp4-compatible
pyffmpegcore profile show audio/podcast-speech --json
pyffmpegcore profile validate ./review-copy.toml
pyffmpegcore profile run web/mp4-compatible --input source.webm --output publish.mp4 --receipt publish.json
```

The built-in registry deliberately stays small:

| Profile | Workflow | Contract |
| --- | --- | --- |
| `web/mp4-compatible` | convert | H.264, AAC, yuv420p, fast-start MP4 |
| `web/small-upload` | compress | conservative H.264/AAC upload starting point |
| `audio/podcast-speech` | normalize audio | speech loudness and true-peak targets |
| `subtitles/accessibility` | add subtitles | labelled subtitle track with copied A/V |
| `archive/mezzanine` | convert | lossless FFV1/FLAC Matroska |

Every profile has a `profile_version`. A new output contract requires a new profile version; an upgrade must not silently change existing behavior.

`profile run` compiles the named built-in profile through the same typed planner,
preflight, executor, machine-result, and receipt layers as the task commands.
The output extension is part of the contract and is validated before mutation.
`subtitles/accessibility` additionally requires `--subtitle captions.srt`.
Every built-in profile runs a golden real-media contract from the exact wheel on
the Linux, macOS, and Windows compatibility matrix.

## Project and user profiles

JSON and TOML use the same strict `1.0` schema. Unknown fields fail validation.

```toml
schema_version = "1.0"
name = "project/review-copy"
profile_version = 1
description = "Small review copy"
workflow = "convert"
required_capabilities = ["encoder:libx264"]

[options]
video_codec = "libx264"
crf = 30
```

Required fields are `schema_version`, `name`, `profile_version`, `description`, `workflow`, and `options`. Names must be namespaced. Options may contain only JSON-compatible data. Capabilities use `kind:name`, such as `encoder:libx264` or `filter:loudnorm`.

Service-specific presets are not accepted into the built-in registry unless the service publishes stable requirements and the project commits to maintaining and testing them. A local profile is the safer place for organization-specific policy.
