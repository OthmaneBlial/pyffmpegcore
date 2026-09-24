# A public 0.3.1 install. 63.4 real seconds.

Recorded on 24 September 2026 from a fresh virtual environment on macOS arm64,
Python 3.14.6, and FFmpeg 9.0.1. The capture installs the exact public `0.3.1`
wheel from PyPI, creates synthetic media, previews a web profile, encodes a
result, probes its streams, and validates its receipt. The repository
validator measured **63.4 seconds** and rejected private home paths.

<div class="pfc-demo-ledger" aria-label="Terminal demonstration facts">
  <div><span>Artifact</span><strong>PyPI 0.3.1</strong></div>
  <div><span>Duration</span><strong>63.4 s</strong></div>
  <div><span>Host</span><strong>macOS arm64</strong></div>
  <div><span>Media</span><strong>Synthetic / local</strong></div>
</div>

## Inspect or replay the evidence

- [Download the original asciicast](assets/terminal-demo-v0.3.1.cast)
- [Read the complete accessible transcript](assets/terminal-demo-v0.3.1.txt)
- [Inspect the signed GitHub release, checksums, and artifact report](https://github.com/OthmaneBlial/pyffmpegcore/releases/tag/v0.3.1)
- [Inspect the exact publication and six-cell public-install workflow](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35975371541)
- [Open the public PyPI files](https://pypi.org/project/pyffmpegcore/0.3.1/)
- [Verify the wheel Trusted Publisher attestation](https://pypi.org/integrity/pyffmpegcore/0.3.1/pyffmpegcore-0.3.1-py3-none-any.whl/provenance)
- [Verify the source distribution Trusted Publisher attestation](https://pypi.org/integrity/pyffmpegcore/0.3.1/pyffmpegcore-0.3.1.tar.gz/provenance)
- [Inspect the archived 0.3.0 recording](assets/terminal-demo-v0.3.0.cast)
- [Inspect the archived 0.2.2 recording](assets/terminal-demo-v0.2.2.cast)

The published wheel is 101,638 bytes with SHA-256
`ea222d3dc5d09ae0ffd79c310ea415eb4edb2d7e04a87532cda939a7890d255d`. The
335,713-byte source distribution has SHA-256
`e0ff591589dd3950e11450dcecc0d1b39718c42415332568e606c98207c94074`. The
release `SHA256SUMS` and PyPI JSON match both artifacts.

To replay the cast with the open-source asciinema client:

```bash
asciinema play terminal-demo-v0.3.1.cast
```

To validate the recording and regenerate its transcript:

```bash
python scripts/validate_terminal_demo.py \
  --cast docs/assets/terminal-demo-v0.3.1.cast \
  --expected-version 0.3.1 \
  --transcript /tmp/terminal-demo-v0.3.1.txt
```

## What the recording proves

1. The installed package came from the public PyPI wheel, checked by SHA-256.
2. `doctor` resolved the real FFmpeg and FFprobe binaries and their capabilities.
3. `smoke-test` generated local synthetic media and verified a thumbnail.
4. `--explain` showed the argument plan and preflight without writing output.
5. The run emitted progress, produced an H.264/AAC MP4, probed its streams, and
   validated the schema 1.0 receipt.

The fixture and output are synthetic. They do not establish quality on user
media or support for every FFmpeg build. No personal media or telemetry was
involved. See the [compatibility policy](COMPATIBILITY.md) and [measured recipe
evidence](evidence.md).
