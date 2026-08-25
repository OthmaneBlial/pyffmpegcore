# Why capability preflight comes before FFmpeg execution

An FFmpeg command can be syntactically valid and still fail because the local
build lacks an encoder, muxer, filter, protocol, or suitable input stream.
Checking only that `ffmpeg` exists moves this failure into the destructive part
of a job, where partial outputs and misleading automation become possible.

PyFFmpegCore inventories the selected binary, maps each typed workflow to
required capabilities, probes the input, checks stream requirements, output
collision, writable space, estimated disk space, and container support, then
returns one versioned `PreflightReport`. Human `--explain` and machine
`--plan-json` views serialize the same facts.

```bash
pyffmpegcore profile run web/mp4-compatible \
  --input source.mov --output web.mp4 \
  --explain
```

If `libx264` is absent, the report names `encoder:libx264` and supplies a tested
fallback or platform remedy when the capability catalog has one. It does not
silently choose a different output contract.

The implementation lives in `pyffmpegcore/capabilities.py` and
`pyffmpegcore/preflight.py`; the cross-platform catalog contract is exercised
by `scripts/validate_capability_catalog.py`. The maintained rules are bounded:
preflight reduces known environmental failure, but it cannot prove subjective
media quality or prevent the operating system from changing after the check.
