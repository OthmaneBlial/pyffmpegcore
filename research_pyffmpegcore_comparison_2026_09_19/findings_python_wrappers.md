# Python FFmpeg wrappers — primary-source findings (19 September 2026)

Scope: documented capabilities of **python-ffmpeg** (`jonghwanhyeon/python-ffmpeg`) and **ffmpegio** (`python-ffmpegio/python-ffmpegio`). These are observations from the linked project documentation, not hands-on performance or compatibility tests. A capability not mentioned here is not presumed absent.

## python-ffmpeg

- Its overview explicitly provides **synchronous and `asyncio` APIs**. Both examples build a conversion with chained `.option()`, `.input()`, and `.output()` calls, then `execute()`/`await execute()`. The API reference documents global, input, and output option dictionaries/keyword arguments and exposes the generated `arguments` list. [Overview](https://python-ffmpeg.readthedocs.io/en/latest/), [API reference](https://python-ffmpeg.readthedocs.io/en/latest/api/)
- Its transcoding examples cover **stream copy/remux** (`codec="copy"`) and **H.264 encoding plus scaling**, each with a `progress` listener. [Transcoding examples](https://python-ffmpeg.readthedocs.io/en/latest/examples/transcoding/)
- Status is available through `start`, `stderr`, `progress`, `completed`, and `terminated` events; the API reference defines progress fields (frame, fps, size, time, bitrate, speed) and `terminate()`. The async API permits coroutine listeners. [Monitoring status](https://python-ffmpeg.readthedocs.io/en/latest/examples/monitoring-status/), [Asynchronous listeners](https://python-ffmpeg.readthedocs.io/en/latest/examples/asynchronous-listeners/), [API reference](https://python-ffmpeg.readthedocs.io/en/latest/api/)
- For **stream I/O**, the documented `pipe:0` input accepts bytes or another stream through `execute(...)`, and `pipe:1` output returns bytes from `execute()`; both have sync and async examples. [Feeding stdin](https://python-ffmpeg.readthedocs.io/en/latest/examples/feeding-data-to-stdin/), [Using stdout](https://python-ffmpeg.readthedocs.io/en/latest/examples/using-output-to-stdout/)

## ffmpegio

- The project describes a Python interface to the system FFmpeg executable for reading, writing, filtering, probing, and transcoding. It documents NumPy or bytes media representations, `ffmpegio.open(...)` stream I/O, FFmpeg options and filter graphs, and progress callbacks. [Official repository README](https://github.com/python-ffmpegio/python-ffmpegio)
- `ffmpegio.transcode(inputs, outputs, ...)` supports multiple input/output specifications, input/output-specific option dictionaries, a progress callback, overwrite/log switches, two-pass encoding, subprocess keyword arguments, and FFmpeg options. If an output is stdout, it can return bytes. Its reference shows a **regular function call**; this source does not establish a native coroutine API, so do not label async support present or absent on this evidence alone. [Basic I/O API reference, `transcode`](https://python-ffmpegio.github.io/python-ffmpegio/basicio.html#ffmpegio.transcode)
- `ffmpegio.open(...)` provides a context-managed link for video/audio stream reading, writing, or filtering, including block-sized reads; the docs show frame and sample loops and say the context manager closes FFmpeg processes and associated threads on exit. The basic read/write/filter functions accept `progress` and FFmpeg options. [Basic I/O API reference, `open`](https://python-ffmpegio.github.io/python-ffmpegio/basicio.html#ffmpegio.open)
- The API reference includes `set_path`, `get_path`, and `is_ready` for the system executables, including optional finder plugins. This is executable discovery, not evidence of a PyFFmpegCore-style preflight or receipt workflow. [Basic I/O API reference](https://python-ffmpegio.github.io/python-ffmpegio/basicio.html)

## Comparison use

Both projects have substantial conversion, option, progress, and pipe/stream capabilities. Distinguish PyFFmpegCore by the **specific preflight → inspectable plan → executed conversion → validated receipt workflow only where this repository has direct evidence**. Do not claim either wrapper cannot implement that workflow, lacks security checks, or is slower; the official pages above do not prove those negatives.
