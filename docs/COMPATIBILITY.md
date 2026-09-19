# Compatibility Policy

PyFFmpegCore supports only combinations backed by visible automated evidence. “Expected to work” is not the same as “tested.”

## Python Policy

Python 3.10 through 3.14 are the supported interpreter versions. Every version runs the package contract on Linux. Python 3.10 and 3.14 are the baseline and newest-version anchors for installed-wheel media smoke tests on all supported operating systems.

End-of-life Python versions are not advertised. A Python version is removed in the next feature release after upstream end of life unless the project documents and continuously tests an explicit exception.

## Operating-System Matrix

| Platform | Python 3.10 | Python 3.11–3.13 | Python 3.14 |
| --- | --- | --- | --- |
| Ubuntu GitHub-hosted runner | Tested: exact-wheel media smoke | Tested: package contract only | Tested: exact-wheel media smoke |
| macOS GitHub-hosted runner | Tested: exact-wheel media smoke | Expected; no current media smoke | Tested: exact-wheel media smoke |
| Windows GitHub-hosted runner | Tested: exact-wheel media smoke | Expected; no current media smoke | Tested: exact-wheel media smoke |

Python 3.9 and older, PyPy, other operating systems, and architectures outside
the tested runners are **not in the support policy**. "Expected" cells have no
cross-platform media result. Even a tested cell proves only the named workflows
on that runner and FFmpeg build.

The [CI workflow](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/ci.yml) is authoritative. A cell counts as tested only when its current required check is green. Compatibility JSON artifacts record the runner architecture, Python version, CLI version, FFmpeg path/version, and FFprobe path/version. The workflow also validates the six artifacts and uploads a readable summary; `python scripts/summarize_compatibility.py <downloaded-artifact-directory> --run-url <run-url>` reproduces it locally.

### Verified snapshot: 19 September 2026

In [run `35448000531`](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35448000531), all six media smoke jobs, the Linux Python 3.10–3.14 package-contract jobs, and the compatibility-summary job passed. The six media jobs installed the **same prebuilt wheel** (`pyffmpegcore-0.2.2-py3-none-any.whl`, SHA-256 `71f40a5f5e11468cf84639f0a91042fead24819d2def4e1ee081987085bb2525`). This is a CI artifact from `c81c54d`, not the published `0.2.2` wheel. Each cell reports 26/26 verified checks: the previous 22 workflows and four expected refusals whose exit codes and remedies were checked. The [generated Markdown artifact](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35448000531) records every cell and its capability gaps.

| Runner | Architecture | Python | FFmpeg reported by `doctor` | Capability catalog gaps |
| --- | --- | --- | --- | --- |
| Ubuntu | x86_64 | 3.10.21 / 3.14.7 | 6.1.1-3ubuntu5 | None reported |
| macOS | arm64 | 3.10.11 / 3.14.7 | 9.0.1 | `encoder:libwebp` and `filter:subtitles` absent |
| Windows | AMD64 | 3.10.11 / 3.14.7 | 9.0.1 essentials build | None reported |

The macOS catalog gaps affect `images/webp` and `subtitles/burn` on that
Homebrew build; those optional capabilities are **not** validated by the
successful profile smoke. No Android, iOS, or physical-device behavior is
implied by this CI snapshot. Runner packages move, so recheck the latest run
before making a release claim.

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

Latest policy update: 2026-09-19. Consult the linked workflows for the latest execution date and exact versions.
