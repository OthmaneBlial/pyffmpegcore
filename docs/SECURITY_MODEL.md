# Command-Execution Security Model

PyFFmpegCore is a local task runner around FFmpeg and FFprobe. It reduces common command-construction mistakes, but it does not make hostile media safe to decode and it is not a sandbox.

## Trust Boundaries

Untrusted data can enter through file and directory paths, media bytes, container metadata, subtitle text, filter arguments, URLs, environment-selected binaries, and output locations. FFmpeg/FFprobe and the operating system remain separate trusted components with their own security updates.

## Command Construction

Runtime process launches use argument arrays with `shell=False` behavior. User-controlled values are never interpolated into a shell command. This prevents normal shell metacharacters in paths from becoming shell syntax.

FFmpeg filter graphs and concat manifests have their own grammars. Values embedded in those grammars require context-specific escaping; shell avoidance alone is not sufficient. New features must prefer separate FFmpeg arguments, constrain values to typed choices or numbers, and test spaces, apostrophes, Unicode, colons, and Windows-style paths where applicable.

## Files, Temporary Data, and Overwrites

Commands reject an existing output unless the user passes `--force`. Temporary work should use private, randomly named directories and be removed after completion. Release and CI scripts must not place credentials or personal media into artifacts. Symlink and time-of-check/time-of-use attacks are not fully prevented when processing in an attacker-controlled directory; use a trusted working directory for hostile inputs.

## URLs and Credentials

Do not put credentials in media URLs or command arguments. Process lists, exceptions, logs, receipts, and CI output may expose them. PyFFmpegCore does not currently provide a secret-redaction guarantee for arbitrary FFmpeg diagnostics.

## Malicious Media and Metadata

FFmpeg parses complex attacker-controlled formats. Keep FFmpeg patched and process hostile media inside an operating-system sandbox or disposable container with minimal permissions. Do not trust titles, filenames, subtitle content, or chapter metadata as safe terminal or HTML text. PyFFmpegCore should render metadata as data and must not evaluate it.

## Resource Exhaustion

Small compressed inputs can require large amounts of CPU, memory, disk, or output bandwidth. The current CLI does not enforce universal time, memory, frame, pixel, or output-size limits. Run untrusted jobs with OS/container quotas and validate media dimensions and duration before expensive work. Future limits must fail closed and appear in plans and receipts.

## Binary Selection

`--ffmpeg-path` and `--ffprobe-path` execute the selected local binaries. Supplying an untrusted executable path is equivalent to executing that program. `doctor` reports the resolved paths so automation can verify the toolchain.

## Security Invariants

- No runtime `shell=True`, `os.system`, or shell-string process launch.
- No silent overwrite.
- Stable exit categories distinguish usage, environment, validation, processing, and partial success.
- Generated fixtures and release artifacts contain no unknown third-party media.
- Releases use signed tags, exact-artifact tests, OIDC Trusted Publishing, checksums, and provenance attestations.

Report a violation privately through the [security policy](https://github.com/OthmaneBlial/pyffmpegcore/blob/main/SECURITY.md).
