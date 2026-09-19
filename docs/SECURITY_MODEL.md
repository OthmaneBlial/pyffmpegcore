# Command-Execution Security Model

PyFFmpegCore is a local task runner around FFmpeg and FFprobe. It reduces common command-construction mistakes, but it does not make hostile media safe to decode and it is not a sandbox.

## Trust Boundaries

Untrusted data can enter through file and directory paths, media bytes, container metadata, subtitle text, filter arguments, URLs, environment-selected binaries, and output locations. FFmpeg/FFprobe and the operating system remain separate trusted components with their own security updates.

## Command Construction

Runtime process launches use argument arrays with `shell=False` behavior. User-controlled values are never interpolated into a shell command. This prevents normal shell metacharacters in paths from becoming shell syntax.

Managed FFmpeg processes receive `-nostdin` and a null standard-input handle.
They cannot enter FFmpeg's interactive command mode or suspend while checking a
CI/background console. Plans expose `-nostdin` so this behavior is reviewable
before execution.

FFmpeg stdout and stderr are decoded explicitly as UTF-8 with replacement for
malformed bytes. Locale-specific decoding cannot terminate a pipe-drain thread
and leave the child process blocked on Unicode media metadata.

FFmpeg filter graphs and concat manifests have their own grammars. Values embedded in those grammars require context-specific escaping; shell avoidance alone is not sufficient. New features must prefer separate FFmpeg arguments, constrain values to typed choices or numbers, and test spaces, apostrophes, Unicode, colons, and Windows-style paths where applicable.

## Files, Temporary Data, and Overwrites

Commands reject an existing output unless the user passes `--force`. Temporary work should use private, randomly named directories and be removed after completion. Release and CI scripts must not place credentials or personal media into artifacts. The GitHub Action rejects existing symlinks in its workspace paths and rechecks artifact paths before upload. Symlink and time-of-check/time-of-use attacks are not fully prevented when another process can change a directory after validation; use a trusted working directory for hostile inputs.

## URLs and Credentials

Single-command CLI workflows reject URL-like media paths; use a pipeline with
`secret_variables` for a remote input. Pipeline inputs preserve the URI for
FFmpeg, while the preflight label and published pipeline results/receipts
redact credentials, URL queries, and embedded URLs in FFmpeg diagnostics.
Remote output URLs are refused by preflight. The Action disables networking by
default; enable it only for an intentional remote source.

Do not put credentials in command arguments. Process lists, exceptions, and
unstructured third-party diagnostics may still expose them. PyFFmpegCore is
not a general secret sandbox, and it cannot guarantee redaction for every
future FFmpeg diagnostic format.

## Malicious Media and Metadata

FFmpeg parses complex attacker-controlled formats. Keep FFmpeg patched and process hostile media inside an operating-system sandbox or disposable container with minimal permissions. Do not trust titles, filenames, subtitle content, or chapter metadata as safe terminal or HTML text. PyFFmpegCore should render metadata as data and must not evaluate it.

## Resource Exhaustion

Small compressed inputs can require large amounts of CPU, memory, disk, or output bandwidth. The CLI offers an explicit `--timeout` for managed media jobs, but does not enforce a universal deadline across a batch or pipeline, nor memory, frame, pixel, or output-size limits. Run untrusted jobs with OS/container quotas and validate media dimensions and duration before expensive work. Future limits must fail closed and appear in plans and receipts.

Managed process pipes are drained in bounded read chunks. The default `TAIL`
capture retains at most `capture_tail_chars` of stdout and stderr per stream;
`DISCARD` retains no published diagnostics, while explicit `FULL` capture can
grow with FFmpeg output. This bounds retained diagnostics, not FFmpeg's memory,
CPU, decoded frames, or bytes written to media outputs. Timeout applies to
managed execution; use an OS or container quota for a hard disk/memory limit.

## Binary Selection

`--ffmpeg-path` and `--ffprobe-path` execute the selected local binaries. Supplying an untrusted executable path is equivalent to executing that program. `doctor` reports the resolved paths so automation can verify the toolchain.

## Security Invariants

- No runtime `shell=True`, `os.system`, or shell-string process launch.
- No interactive standard input for managed FFmpeg jobs.
- No silent overwrite.
- Stable exit categories distinguish usage, environment, validation, processing, and partial success.
- Generated fixtures and release artifacts contain no unknown third-party media.
- Releases use signed tags, exact-artifact tests, OIDC Trusted Publishing, checksums, and provenance attestations.

Report a violation privately through the [security policy](https://github.com/OthmaneBlial/pyffmpegcore/blob/main/SECURITY.md).
