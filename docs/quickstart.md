# Five-minute start

This flow needs no repository checkout and no personal media.

## 1. Install the public beta

```bash
pipx install "pyffmpegcore==0.3.0"
```

Version `0.3.0` is the signed public beta. Pinning it keeps this proof
reproducible; its exact wheel passed the project's cross-platform release gate.

## 2. Diagnose the media stack

```bash
pyffmpegcore doctor
```

The command reports Python, operating system, FFmpeg/FFprobe paths and versions, capability counts, hardware accelerators, and any missing optional core capability.

## 3. Generate a sample clip

```bash
pyffmpegcore smoke-test --keep-dir pyffmpegcore-demo
```

The smoke test creates a short synthetic clip at
`pyffmpegcore-demo/synthetic-input.mp4`. It also checks a thumbnail. It needs
neither a repository checkout nor personal media. On a fresh run, it reports
`Smoke test: PASS`; codec details depend on the installed FFmpeg build.

## 4. Preview and produce a web MP4

The following commands work as written in Bash, zsh, and PowerShell. Preview
first; `--explain` does not create `web.mp4`.

```bash
pyffmpegcore profile run web/mp4-compatible --input pyffmpegcore-demo/synthetic-input.mp4 --output pyffmpegcore-demo/web.mp4 --explain
pyffmpegcore profile run web/mp4-compatible --input pyffmpegcore-demo/synthetic-input.mp4 --output pyffmpegcore-demo/web.mp4 --receipt pyffmpegcore-demo/web.receipt.json
```

This profile targets a browser-compatible H.264/AAC MP4. The CLI refuses to
replace an existing output unless you explicitly add `--force`. This step
requires an FFmpeg build with `libx264` and `aac` encoders; `doctor --json`
lists the capabilities of your selected binary. If either is absent, see
[installation help](installation.md) and use a build that provides them.

## 5. Check the result and receipt

```bash
pyffmpegcore probe --input pyffmpegcore-demo/web.mp4 --json
pyffmpegcore receipt validate pyffmpegcore-demo/web.receipt.json --json
```

Check the `video.codec` and `audio.codec` fields in the probe output and
`"valid": true` in the receipt validation output. The file duration and size
depend on your FFmpeg build. You can inspect the generated input with
`pyffmpegcore probe --input pyffmpegcore-demo/synthetic-input.mp4 --json`.
Remove `pyffmpegcore-demo` when finished. A plain `smoke-test` cleans up its
temporary files automatically.

## 6. Run a task on your own file

```bash
pyffmpegcore convert --input clip.webm --output clip.mp4 --video-codec libx264 --audio-codec aac
```

Use `probe` before and after when streams or metadata matter. See
[installation help](installation.md) if `doctor` reports a missing FFmpeg
binary or encoder.

Next: [web-compatible video](recipes/web-video.md), [audio extraction](recipes/audio-extraction.md), or [exact-size compression](recipes/exact-size.md).
