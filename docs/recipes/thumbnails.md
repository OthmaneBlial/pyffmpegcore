# Create thumbnails

Generate the deterministic practice fixture before running this recipe:

```bash
python tests/media/download_fixtures.py --force
```

Create a 640-pixel-wide JPEG thumbnail and save both a machine-readable result
and a privacy-redacted receipt:

```bash
pyffmpegcore thumbnail \
	--input tests/media/downloads/sample_mp4_h264.mp4 \
	--output thumbnail.jpg \
	--timestamp 00:00:01 \
	--width 640 \
	--receipt thumbnail.receipt.json \
	--result-json > thumbnail.result.json
```

The result JSON proves that the command succeeded. Use the separate probe
command to obtain machine-readable proof of the image codec and requested
width:

```bash
pyffmpegcore probe --input thumbnail.jpg --json
```

The output should report `mjpeg` for `video.codec` and `640` for
`video.width`. The same facts are available in the receipt at
`items[0].output_probe.streams[0].codec` and
`items[0].output_probe.streams[0].width`.

Validate the redacted receipt without accessing the media again:

```bash
pyffmpegcore receipt validate thumbnail.receipt.json --json
```

The validation result should contain `"valid": true`.

The requested timestamp must exist in the source. Supplying both width and
height forces those dimensions; supplying one preserves the aspect ratio
according to FFmpeg scale rules.

The CLI refuses to overwrite an existing thumbnail or receipt by default. Run
the command again with `--force` when replacement is intentional:

```bash
pyffmpegcore thumbnail \
	--input tests/media/downloads/sample_mp4_h264.mp4 \
	--output thumbnail.jpg \
	--timestamp 00:00:01 \
	--width 640 \
	--receipt thumbnail.receipt.json \
	--force
```

For a synthetic input that is safe to share in a bug report:

```bash
pyffmpegcore smoke-test --keep-dir synthetic-demo
```

That command already verifies the generated thumbnail with FFprobe.
