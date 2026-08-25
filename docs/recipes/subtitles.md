# Subtitle workflows

## Add a selectable track

```bash
pyffmpegcore subtitles add --video lesson.mp4 --subtitle captions.srt --output lesson-captioned.mp4 --language eng
```

## Extract an embedded track

```bash
pyffmpegcore subtitles extract --video lesson-captioned.mp4 --output extracted.srt --stream-index 0
```

## Burn text into video

```bash
pyffmpegcore subtitles burn --video lesson.mp4 --subtitle captions.srt --output lesson-burned.mp4
```

Selectable subtitles can be preserved separately; burned subtitles permanently change video pixels. The FFmpeg build must provide the relevant subtitle decoder/muxer and the `subtitles` filter for burning. Paths embedded in filter syntax receive separate escaping from normal process arguments.
