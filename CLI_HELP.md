# CLI Help

This is the copy-paste command guide for the `pyffmpegcore` terminal app.

## Quick Commands

Check that the CLI and FFmpeg are visible:

```bash
pyffmpegcore --version
pyffmpegcore doctor
```

Inspect a file before changing it:

```bash
pyffmpegcore probe --input my-video.mp4
pyffmpegcore probe --input my-video.mp4 --json
```

Convert a WebM or MOV into MP4:

```bash
pyffmpegcore convert --input input.webm --output output.mp4 --video-codec libx264 --audio-codec aac
```

Compress a large MP4:

```bash
pyffmpegcore compress --input large-video.mp4 --output smaller-video.mp4 --crf 28
```

Extract MP3 audio from a video:

```bash
pyffmpegcore extract-audio --input interview.mp4 --output interview.mp3
```

Create a thumbnail:

```bash
pyffmpegcore thumbnail --input input.mp4 --output thumb.jpg --timestamp 00:00:01 --width 640
```

Generate a waveform image:

```bash
pyffmpegcore waveform --input podcast.mp3 --output waveform.png --width 1200 --height 300
```

Burn subtitles into a video:

```bash
pyffmpegcore subtitles burn --video input.mp4 --subtitle captions.srt --output burned.mp4
```

Join matching clips quickly:

```bash
pyffmpegcore concat --inputs part1.mp4 part2.mp4 part3.mp4 --output joined.mp4 --mode copy
```

## Find More Help

Use command-specific help when you need the full option list:

```bash
pyffmpegcore --help
pyffmpegcore convert --help
pyffmpegcore subtitles --help
pyffmpegcore mix-audio background --help
```

## Shell Completion

Generate a completion script:

```bash
pyffmpegcore completion bash
pyffmpegcore completion zsh
pyffmpegcore completion powershell
```

Example install for Bash:

```bash
mkdir -p ~/.local/share/bash-completion/completions
pyffmpegcore completion bash > ~/.local/share/bash-completion/completions/pyffmpegcore
```

Example install for Zsh:

```bash
mkdir -p ~/.zfunc
pyffmpegcore completion zsh > ~/.zfunc/_pyffmpegcore
```

Example install for PowerShell:

```powershell
pyffmpegcore completion powershell | Out-File -Encoding utf8 $HOME\Documents\WindowsPowerShell\pyffmpegcore-completion.ps1
```
