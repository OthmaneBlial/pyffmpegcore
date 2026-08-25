# Normalize podcast speech

Use EBU R128 loudness normalization for a consistent speech-oriented deliverable.

```bash
pyffmpegcore normalize-audio --input episode.wav --output episode-normalized.wav --method loudnorm
```

For an MP3 deliverable:

```bash
pyffmpegcore normalize-audio --input episode.wav --output episode-normalized.mp3 --method loudnorm
```

Listen to the complete result and compare clipping, noise, and quiet sections. Loudness normalization cannot repair a distorted recording and should not be advertised as mastering.

MP3 output currently uses the maintained 192 kbps workflow default. See the
[dated loudness proof and redacted receipt](../evidence.md#reproducible-recipe-evidence).
