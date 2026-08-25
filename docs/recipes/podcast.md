# Normalize podcast speech

Use EBU R128 loudness normalization for a consistent speech-oriented deliverable.

```bash
pyffmpegcore normalize-audio --input episode.wav --output episode-normalized.wav --method loudnorm
```

For an MP3 deliverable:

```bash
pyffmpegcore normalize-audio --input episode.wav --output episode-normalized.mp3 --method loudnorm --bitrate 192k
```

Listen to the complete result and compare clipping, noise, and quiet sections. Loudness normalization cannot repair a distorted recording and should not be advertised as mastering.
