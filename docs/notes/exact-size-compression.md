# Exact-size compression is a budget, not magic

“Make this video smaller than 24 MiB” is not equivalent to choosing a CRF.
PyFFmpegCore converts the target to bytes, reserves container overhead and audio
bitrate, derives the remaining video bitrate from probed duration, and rejects
an impossible request before mutation when that budget falls below the declared
quality floor.

```text
usable bits = target bytes × 8 × (1 - container reserve)
video bitrate = usable bits / duration - audio bitrate
```

The maintained workflow uses two-pass encoding when requested, keeps pass files
in a controlled temporary workspace, and cleans them according to the explicit
temporary-file policy. After muxing, the result and receipt use the actual file
size to report `target_size_bytes` and `target_met`; an estimate is never
reported as final proof.

The [dated fixture run](../evidence.md) reduced a 4,042,503-byte H.264/AAC input
to 248,417 bytes against a 262,144-byte limit. That proves the implementation
on one deterministic input and FFmpeg build, not that every quality target is
feasible. Users still need to watch/listen to the output.
