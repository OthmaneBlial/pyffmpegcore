# Create thumbnails

```bash
pyffmpegcore thumbnail --input demo.mp4 --output thumbnail.jpg --timestamp 00:00:01 --width 640
pyffmpegcore probe --input thumbnail.jpg --json
```

The requested timestamp must exist in the source. Supplying both width and height forces those dimensions; supplying one preserves the aspect ratio according to FFmpeg scale rules.

For a synthetic input that is safe to share in a bug report:

```bash
pyffmpegcore smoke-test --keep-dir synthetic-demo
```

That command already verifies the generated thumbnail with FFprobe.
