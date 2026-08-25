# Recipes by outcome

Every supported recipe names an input contract, command, expected output, and machine-verifiable checks.

- [Web-compatible video](web-video.md)
- [Fit an upload under a target size](exact-size.md)
- [Preserve every audio, subtitle, attachment, and data stream](preserve-streams.md)
- [Extract audio](audio-extraction.md)
- [Normalize podcast speech](podcast.md)
- [Add, extract, or burn subtitles](subtitles.md)
- [Create thumbnails](thumbnails.md)
- [Convert image batches](image-batches.md)

## Built from repeated user problems

These are not invented demo categories. Independent FFmpeg users repeatedly
ask why [MP4 works locally but not in browsers](https://stackoverflow.com/questions/24693751/html5-video-ffmpeg-encoded-mp4-not-playing-in-any-browser-plays-in-vlc-though),
how to [fit a complete video under a size limit](https://stackoverflow.com/questions/29082422/ffmpeg-video-compression-specific-file-size/61146975),
and why [secondary tracks disappear](https://superuser.com/questions/1513289/track-2-and-sub-titles-lost-in-ffmpeg-conversion).
Each linked PyFFmpegCore recipe turns one of those clusters into an inspectable
plan, a deterministic media test, and explicit verification steps.

Use `probe` before and after. If the input has multiple audio tracks, chapters,
attachments, rotation, HDR metadata, or cover art, verify what the workflow
preserves before deleting the source.
