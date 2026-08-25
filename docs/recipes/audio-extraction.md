# Extract audio

The output extension selects a sensible default codec when no codec is specified.

```bash
pyffmpegcore extract-audio --input interview.mp4 --output interview.mp3
pyffmpegcore probe --input interview.mp3 --json
```

For uncompressed editing audio:

```powershell
pyffmpegcore extract-audio --input "interview.mp4" --output "interview.wav" --sample-rate 48000 --channels 2
```

Python:

```python
from pyffmpegcore import FFmpegRunner

result = FFmpegRunner().extract_audio("interview.mp4", "interview.wav", sample_rate=48000, channels=2)
assert result.returncode == 0, result.stderr
```

Verify that the output contains audio and no video stream.
