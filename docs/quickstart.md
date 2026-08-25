# Five-minute start

This flow needs no repository checkout and no personal media.

## 1. Install the current evaluation build

```bash
pipx install git+https://github.com/OthmaneBlial/pyffmpegcore.git@main
```

## 2. Diagnose the media stack

```bash
pyffmpegcore doctor
```

The command reports Python, operating system, FFmpeg/FFprobe paths and versions, capability counts, hardware accelerators, and any missing optional core capability.

## 3. Prove one complete job

```bash
pyffmpegcore smoke-test
```

Representative output from the real smoke path:

```text
Smoke test: PASS
Synthetic input: mpeg4 320x180
Verified thumbnail: 160x90
Artifacts: cleaned up
```

Codec details and byte counts depend on the installed FFmpeg build. The success criteria do not.

To inspect the generated media:

```bash
pyffmpegcore smoke-test --keep-dir pyffmpegcore-demo
pyffmpegcore probe --input pyffmpegcore-demo/synthetic-input.mp4 --json
```

Remove the retained directory when finished. Without `--keep-dir`, the smoke command cleans up automatically.

## 4. Run a useful task on your file

```bash
pyffmpegcore convert --input clip.webm --output clip.mp4 --video-codec libx264 --audio-codec aac
```

PyFFmpegCore refuses to replace `clip.mp4` unless you explicitly add `--force`. Use `probe` before and after when streams or metadata matter.

Next: [web-compatible video](recipes/web-video.md), [audio extraction](recipes/audio-extraction.md), or [exact-size compression](recipes/exact-size.md).
