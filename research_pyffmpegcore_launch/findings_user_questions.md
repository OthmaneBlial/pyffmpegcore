# Repeated FFmpeg/Python user problems converted into product contracts

Checked: 2026-08-26. The goal was to find independently reported user
problems, not to manufacture testimonials or infer PyFFmpegCore users that do
not yet exist. Question pages are treated as evidence of the problem; current
PyFFmpegCore code, deterministic fixtures, and cross-platform artifact checks
are the evidence for the implemented response.

## Cluster 1 — rich media loses secondary streams

Independent questions from 2014–2023 report missing secondary audio tracks,
subtitles, and confusion around explicit stream maps:

- https://superuser.com/questions/811939/ffmpeg-convert-and-keep-audio-track
- https://superuser.com/questions/1406666/how-to-get-all-subtitle-streams-recorded-in-ffmpeg/1625114
- https://superuser.com/questions/1513289/track-2-and-sub-titles-lost-in-ffmpeg-conversion
- https://superuser.com/questions/1808132/how-to-copy-the-video-covert-all-audio-streams-to-ac3-and-only-keep-the-subtit

Product response: `convert --preserve-all-streams` maps input `0`, stream-copies
every mapped stream, preserves compatible metadata/chapters, rejects
conflicting re-encoding controls, explains the container-compatibility risk,
and has a real-media regression test covering two audio languages, subtitles,
Unicode metadata, and chapters.

## Cluster 2 — MP4 exists but web playback is unreliable

Independent questions from 2012–2019 report local playback succeeding while
browser playback fails, incompatible pixel formats, and delayed starts caused
by MP4 index placement:

- https://stackoverflow.com/questions/13513621/creating-chrome-compatible-mp4-with-ffmpeg-from-commandline
- https://stackoverflow.com/questions/32829514/which-pixel-format-for-web-mp4-video
- https://stackoverflow.com/questions/54335106/ffmpeg-video-conversion-to-mp4-works-everywhere-except-in-ios-safari-chrome/54335942
- https://superuser.com/questions/851316/swapping-index-of-an-mp4-file-with-ffmpeg

Product response: the maintained `web/mp4-compatible` profile uses H.264, AAC,
YUV 4:2:0, and MP4 fast-start behavior, and the recipe separates media facts
from server requirements such as content type and byte ranges.

## Cluster 3 — a complete upload must fit a byte ceiling

Independent questions from 2015–2021 ask for a specific output size, explain
that `-fs` can truncate or overshoot, and converge on duration-aware two-pass
bitrate planning:

- https://stackoverflow.com/questions/29082422/ffmpeg-video-compression-specific-file-size/61146975
- https://stackoverflow.com/questions/59051058/limit-file-size-in-ffmpeg
- https://superuser.com/questions/1225044/ffmpeg-conversion-from-webm-to-mp4-how-to-keep-file-size
- https://stackoverflow.com/questions/68608701/targeting-a-specific-file-size-in-vp8vorbis-encoding-using-ffmpeg

Product response: the exact-size workflow computes a feasible video bitrate
from duration, target bytes, audio allocation, overhead reserve, and a minimum
quality floor; it performs two named passes and reports measured PASS/MISS proof
instead of claiming mathematically exact output.

## Cluster 4 — Python/background FFmpeg hangs

Independent questions from 2013–2024 identify full stdout/stderr pipes,
interactive stdin, and decoding errors as recurring causes:

- https://stackoverflow.com/questions/16523746/ffmpeg-hangs-when-run-in-background/16527559
- https://stackoverflow.com/questions/40964071/piping-to-ffmpeg-with-python-subprocess-freezes
- https://stackoverflow.com/questions/60606499/python-gets-stuck-at-pipe-stdin-writeimage-tostring
- https://stackoverflow.com/questions/78428899/python-3-using-ffmpeg-in-a-subprocess-getting-stderr-decoding-error

Product response: managed processes drain both pipes concurrently, pass
`-nostdin`, attach a null stdin, decode FFmpeg text as UTF-8 with replacement,
and enforce optional timeouts. Windows artifact validation reproduced and then
proved the Unicode pipe-drain fix.

## Promotion rule

These sources justify a product problem and a tested recipe. They do not grant
permission to post promotional answers on those sites. The launch runbook's
affiliation and anti-spam rules still apply.
