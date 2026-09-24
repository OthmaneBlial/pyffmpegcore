# A public 0.3.0 install. 63.5 real seconds.

This terminal capture was recorded on 24 September 2026 from a fresh virtual
environment on macOS arm64, Python 3.14.6, and FFmpeg 9.0.1. It installs the
exact public `0.3.0` wheel from PyPI, creates synthetic media, previews a web
profile, encodes a result, probes its streams, and validates its receipt. The
repository validator measured **63.5 seconds** and rejected private home paths.

<div class="pfc-demo-ledger" aria-label="Terminal demonstration facts">
  <div><span>Artifact</span><strong>PyPI 0.3.0</strong></div>
  <div><span>Duration</span><strong>63.5 s</strong></div>
  <div><span>Host</span><strong>macOS arm64</strong></div>
  <div><span>Media</span><strong>Synthetic / local</strong></div>
</div>

## Inspect or replay the evidence

- [Download the original asciicast](assets/terminal-demo-v0.3.0.cast)
- [Read the complete accessible transcript](assets/terminal-demo-v0.3.0.txt)
- [Inspect the signed GitHub prerelease, checksums, and artifact report](https://github.com/OthmaneBlial/pyffmpegcore/releases/tag/v0.3.0)
- [Inspect the exact publication and six-cell public-install workflow](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35971504440)
- [Open the public PyPI files](https://pypi.org/project/pyffmpegcore/0.3.0/)
- [Verify the wheel Trusted Publisher attestation](https://pypi.org/integrity/pyffmpegcore/0.3.0/pyffmpegcore-0.3.0-py3-none-any.whl/provenance)
- [Inspect the archived 0.2.2 recording and transcript](assets/terminal-demo-v0.2.2.cast)

The published wheel is 101,305 bytes with SHA-256
`8ed1b315b3326cc115e5df4bd1ac32d69b6c77175663d6c630cf3e75c3186df7`.
That hash matches both the PyPI JSON and the release's `SHA256SUMS` file.

To replay the cast with the open-source asciinema client:

```bash
asciinema play terminal-demo-v0.3.0.cast
```

To validate the recording and regenerate its transcript:

```bash
python scripts/validate_terminal_demo.py \
  --cast docs/assets/terminal-demo-v0.3.0.cast \
  --expected-version 0.3.0 \
  --transcript /tmp/terminal-demo-v0.3.0.txt
```

## What the recording proves

1. The installed package came from the public PyPI wheel, checked by SHA-256.
2. `doctor` resolved the real FFmpeg and FFprobe binaries and their capabilities.
3. `smoke-test` generated a local synthetic input and verified a thumbnail.
4. `--explain` showed the argument plan and preflight without writing output.
5. The run emitted progress and produced a 60.02-second H.264/AAC MP4 at
   320×180, reported as 2.5 MB.
6. The receipt validator accepted schema 1.0 and the recorded item.

The fixture and measured output are synthetic. They do not establish quality
on user media or support for every FFmpeg build. No personal media or telemetry
was involved. See the [compatibility policy](COMPATIBILITY.md) and [measured
recipe evidence](evidence.md).
