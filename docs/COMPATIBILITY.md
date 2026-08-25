# Compatibility Policy

PyFFmpegCore supports only combinations backed by visible automated evidence. “Expected to work” is not the same as “tested.”

## Python Policy

Python 3.10 through 3.14 are the supported interpreter versions. Every version runs the package contract on Linux. Python 3.10 and 3.14 are the baseline and newest-version anchors for installed-wheel media smoke tests on all supported operating systems.

End-of-life Python versions are not advertised. A Python version is removed in the next feature release after upstream end of life unless the project documents and continuously tests an explicit exception.

## Operating-System Matrix

| Platform | Python 3.10 | Python 3.11–3.13 | Python 3.14 |
| --- | --- | --- | --- |
| Ubuntu GitHub-hosted runner | Exact-wheel media smoke | Package contract | Exact-wheel media smoke |
| macOS GitHub-hosted runner | Exact-wheel media smoke | Expected to work | Exact-wheel media smoke |
| Windows GitHub-hosted runner | Exact-wheel media smoke | Expected to work | Exact-wheel media smoke |

The [CI workflow](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/ci.yml) is authoritative. A cell counts as tested only when its current required check is green. Compatibility JSON artifacts record the runner architecture, Python version, CLI version, FFmpeg path/version, and FFprobe path/version.

## FFmpeg Policy

PyFFmpegCore does not bundle FFmpeg. CI tests the FFmpeg package available from the current Ubuntu, Homebrew, and Chocolatey runner channels. The exact versions are captured by `pyffmpegcore doctor --json`; therefore, this page deliberately avoids pretending that a moving system package is one fixed version.

Expected baseline behavior requires:

- `ffmpeg` and `ffprobe` executables on `PATH`, or explicit binary paths;
- common demuxers/muxers for MP4, MOV, WebM, MP3, WAV, PNG, and JPEG;
- representative encoders such as H.264, AAC, VP9, Opus, MP3, PCM, and image codecs for the selected workflow;
- filters required by the selected task.

Optional filters and encoders vary by build. Tests skip a capability only when the environment reports that it is absent, and the skip remains visible. A missing optional capability is not silently advertised as supported.

## Scheduled Drift Detection

The [scheduled cold-fixture workflow](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/fixtures.yml) regenerates fixtures without cache reuse and runs representative media jobs on all three operating systems every week. Failures indicate runner, package-manager, Python, or FFmpeg drift that must be triaged before the next release.

Latest policy update: 2026-08-25. Consult the linked workflows for the latest execution date and exact versions.
