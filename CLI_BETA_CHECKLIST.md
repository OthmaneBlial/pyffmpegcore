# CLI Beta Checklist

Acceptance date: 2026-03-28

Acceptance workspace: `/tmp/pyffmpegcore-cli-beta-LwSYJH`

## Release Gate

- [x] Fresh media fixtures downloaded into `/tmp/pyffmpegcore-cli-beta-LwSYJH/fresh fixtures` with `tests/media/download_fixtures.py --output-dir ... --force`
- [x] CLI artifacts built from the repository into `/tmp/pyffmpegcore-cli-beta-LwSYJH/dist`
- [x] Fresh virtual environment created and the wheel installed into it
- [x] `pyffmpegcore --help` and `pyffmpegcore convert --help` produced readable output
- [x] `pyffmpegcore probe --input missing.mp4` returned exit code `4` with the message `Input path does not exist: ...`
- [x] `pyffmpegcore doctor --json` reported both `ffmpeg` and `ffprobe` as available
- [x] `pipx install --suffix=-beta-verify --force <wheel>` succeeded
- [x] `pipx uninstall pyffmpegcore-beta-verify` succeeded

## Acceptance Commands Run

Installed from the built wheel, then executed these public commands end to end on freshly downloaded media:

- `pyffmpegcore probe --input sample_mp4_h264.mp4 --json`
- `pyffmpegcore convert --input sample_webm_vp9.webm --output "converted clip.mp4" --video-codec libx264 --audio-codec aac`
- `pyffmpegcore compress --input sample_mp4_h264.mp4 --output "compressed clip.mp4" --crf 28`
- `pyffmpegcore extract-audio --input sample_mp4_h264.mp4 --output "audio clip.mp3"`
- `pyffmpegcore thumbnail --input sample_mp4_h264.mp4 --output "thumb one.jpg" --timestamp 00:00:01 --width 640`
- `pyffmpegcore waveform --input sample_audio_mp3.mp3 --output "waveform image.png" --width 1200 --height 300`
- `pyffmpegcore speed video --input sample_mp4_h264.mp4 --output "faster video.mp4" --factor 1.5`
- `pyffmpegcore speed audio --input sample_audio_mp3.mp3 --output "faster audio.mp3" --factor 1.25`
- `pyffmpegcore concat --mode reencode --inputs sample_mp4_h264.mp4 sample_webm_vp9.webm --output "joined safe.mp4"`
- `pyffmpegcore subtitles burn --video sample_mp4_h264.mp4 --subtitle sample_subtitles.srt --output "burned subtitles.mp4"`
- `pyffmpegcore mix-audio background --main-input sample_audio_wav.wav --background-input sample_audio_mp3.mp3 --output "background mix.mp3" --bg-volume 0.2`
- `pyffmpegcore normalize-audio --input sample_audio_mp3.mp3 --output "normalized audio.mp3" --method loudnorm`
- `pyffmpegcore images webp --input-dir "image inputs" --output-dir "webp images" --quality 80`

All output paths were created under `/tmp/pyffmpegcore-cli-beta-LwSYJH/outputs with spaces`.

## Output Verification

Produced files:

- `converted clip.mp4`
- `compressed clip.mp4`
- `audio clip.mp3`
- `thumb one.jpg`
- `waveform image.png`
- `faster video.mp4`
- `faster audio.mp3`
- `joined safe.mp4`
- `burned subtitles.mp4`
- `background mix.mp3`
- `normalized audio.mp3`
- `webp images/sample one.webp`
- `webp images/sample two.webp`

Representative `ffprobe` results from the acceptance workspace:

- `converted clip.mp4`: MP4 container, `5.765000s`, `3927234` bytes
- `compressed clip.mp4`: MP4 container, `5.758005s`, `2435429` bytes
- `audio clip.mp3`: MP3 container, `5.799184s`, `93142` bytes
- `faster video.mp4`: MP4 container, `3.866667s`, `3704308` bytes
- `faster audio.mp3`: MP3 container, `2.586122s`, `62737` bytes
- `joined safe.mp4`: MP4 container, `11.523991s`, `8683393` bytes
- `burned subtitles.mp4`: MP4 container, `5.758549s`, `3535281` bytes
- `background mix.mp3`: MP3 container, `3.239184s`, `78411` bytes
- `normalized audio.mp3`: MP3 container, `3.240000s`, `78381` bytes

Decode verification completed with `ffmpeg -v error -i <output> -f null -` for the main video and audio outputs above.

## Artifact Summary

Built artifacts:

- `pyffmpegcore-0.1.2-py3-none-any.whl`
  - SHA256: `ce196b8f5d4f92036f318f907f04c7e5cb5c65180342a6720b4055a58b045303`
  - size: `28051` bytes
- `pyffmpegcore-0.1.2.tar.gz`
  - SHA256: `61d1b30eea806c2e96c4f222e7cabe42c8046b343a36f2e394ed062d06a3d39d`
  - size: `64593` bytes

## Honest Caveats

- This final beta acceptance pass was run locally on Linux.
- macOS and Windows are covered by the new CI clean-install matrix, but that matrix was not executed inside this terminal session.
- Validation here was terminal-only, so human playback review in a desktop media player was not part of this pass.
- The acceptance bar in this session was fresh downloads, clean installation, help and error checks, artifact probing, and decode validation.
