# One public artifact. Sixty-three real seconds.

This terminal recording was captured on 2026-08-26 from a fresh virtual
environment. It downloaded `pyffmpegcore==0.2.1` from public PyPI, used the
machine's local FFmpeg, generated synthetic media, and completed the entire
plan-to-receipt path. The recording validator measured **63.0 seconds** and
rejected private home-directory paths.

<div class="pfc-demo-ledger" aria-label="Terminal demonstration facts">
  <div><span>Artifact</span><strong>PyPI 0.2.1</strong></div>
  <div><span>Duration</span><strong>63.0 s</strong></div>
  <div><span>Media</span><strong>Synthetic</strong></div>
  <div><span>Result</span><strong>PASS</strong></div>
</div>

<div class="pfc-demo-terminal" aria-label="Excerpt from the validated terminal transcript">
  <div class="pfc-demo-terminal__bar"><span>PUBLIC PROOF / DARWIN ARM64</span><span>● VERIFIED</span></div>
  <pre><code>$ demo-env/bin/python -m pip install pyffmpegcore==0.2.1
Successfully installed pyffmpegcore-0.2.1

$ demo-env/bin/pyffmpegcore doctor
ffmpeg: OK
ffprobe: OK

$ demo-env/bin/pyffmpegcore smoke-test --keep-dir media
Smoke test: PASS

Plan 1.0 — convert
Preflight PASS — convert
Progress: 100% complete
Output: media/web.mp4
Receipt: media/web.receipt.json
Valid receipt: schema 1.0, 1 item(s)

PASS — public install, preflight, plan, progress, output, and receipt all verified.</code></pre>
</div>

## Inspect or replay the evidence

- [Download the original asciicast](assets/terminal-demo-v0.2.1.cast)
- [Read the complete accessible transcript](assets/terminal-demo-v0.2.1.txt)
- [Inspect the public release workflow](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/32952883204)
- [Inspect the signed release and checksums](https://github.com/OthmaneBlial/pyffmpegcore/releases/tag/v0.2.1)

To replay the cast locally with the open-source asciinema client:

```bash
asciinema play terminal-demo-v0.2.1.cast
```

## What the recording proves

1. The package comes from public PyPI rather than the repository checkout.
2. `doctor` resolves the actual FFmpeg and FFprobe binaries and indexes their capabilities.
3. `smoke-test` creates and verifies a useful synthetic-media result without personal files.
4. `--explain` reveals the exact argument vector and trade-offs before mutation.
5. The run emits structured progress, probes the output, and writes a privacy-redacted receipt.
6. The receipt validator accepts the resulting schema and item count.

The recording does not claim that every FFmpeg build exposes identical codecs
or filters. That boundary remains visible in the [compatibility policy](COMPATIBILITY.md).
