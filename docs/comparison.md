# Choosing a Python media tool

Reviewed against the projects' own documentation on **19 September 2026**.
This is a comparison of working styles, not a speed benchmark or a claim that
another tool cannot implement a PyFFmpegCore workflow. All five alternatives
expose useful FFmpeg capabilities; the right choice depends on the task.

## One concrete job

The task is to turn a generated VP9 WebM into a web MP4, inspect the proposed
command before writing, then retain evidence of the result. From a clean
repository checkout with the installed PyFFmpegCore `0.2.2` wheel, the replay
used these commands (choose fresh output names when repeating it):

```bash
python tests/media/download_fixtures.py --force
pyffmpegcore doctor --json
pyffmpegcore profile run web/mp4-compatible \
  --input tests/media/downloads/sample_webm_vp9.webm \
  --output web-from-vp9.mp4 --explain
pyffmpegcore profile run web/mp4-compatible \
  --input tests/media/downloads/sample_webm_vp9.webm \
  --output web-from-vp9.mp4 --receipt web-from-vp9.receipt.json
pyffmpegcore probe --input web-from-vp9.mp4 --json
pyffmpegcore receipt validate web-from-vp9.receipt.json --json
```

On macOS arm64, Python 3.14.6, and FFmpeg 9.0.1, the output probed as H.264/AAC,
the receipt validated, and a full FFmpeg decode passed. Its size was
3,814,506 bytes, **78.2% larger** than the 2,141,004-byte source. This profile
targets playback compatibility; it does not promise compression. The
[dated replay index](evidence/recipe-proof-2026-09-19.json) and
[receipt](evidence/web-from-vp9-2026-09-19.receipt.json) let readers inspect
the exact synthetic result. We did not run the five alternatives on this
fixture, so there is no comparative timing, quality, or output-size claim.

## Which tool fits?

| Tool | Capabilities documented by its maintainers | Reach for it when... |
| --- | --- | --- |
| [FFmpeg CLI](https://ffmpeg.org/ffmpeg.html) with [ffprobe](https://ffmpeg.org/ffprobe.html) | Full transcoding, stream mapping and filters; `ffprobe` can emit JSON; FFmpeg exposes `-progress` and `-report`. | You already know and review the required argument vector, or need options outside PyFFmpegCore's maintained tasks. Its primitives can be composed into your own checks and evidence. |
| [ffmpeg-python](https://github.com/kkroening/ffmpeg-python) | Builds directed filter graphs, exposes `probe`, `get_args`/`compile`, and runs FFmpeg synchronously or asynchronously. [API](https://kkroening.github.io/ffmpeg-python/) | Python code needs custom graph construction and direct control over FFmpeg options. You can build your own preflight and receipt around those primitives. |
| [python-ffmpeg](https://python-ffmpeg.readthedocs.io/en/latest/) | Fluent synchronous and `asyncio` builders, an `arguments` list, progress/events, termination, and pipe input/output. [API](https://python-ffmpeg.readthedocs.io/en/latest/api/) | Your application wants a fluent command builder or async event handling. Its documented events and arguments can feed a custom audit record. |
| [ffmpegio](https://github.com/python-ffmpegio/python-ffmpegio) | Transcoding with multiple inputs/outputs, option dictionaries, two-pass support and progress callbacks; context-managed video/audio stream I/O. [API](https://python-ffmpegio.github.io/python-ffmpegio/basicio.html) | You need broad FFmpeg option access, stream readers/writers, or NumPy/bytes-oriented media processing. |
| [PyAV](https://pyav.basswood.io/docs/stable/) | FFmpeg library bindings for containers, streams, packets, frames, decoding/encoding, remuxing and filters. [Container API](https://pyav.basswood.io/docs/stable/api/container.html), [NumPy examples](https://pyav.basswood.io/docs/stable/cookbook/numpy.html) | Python must inspect or change individual packets or frames, for example image analysis or frame-by-frame transformations. |
| **PyFFmpegCore** | This repository's tested preflight → inspectable typed plan → maintained task → redacted, validated receipt, shared across CLI, Python and CI. | Your job matches a maintained profile or workflow and you want that complete operational path without building its policy and evidence layer yourself. |

**What the distinction means:** the other projects' documented APIs provide
many of the same building blocks. PyFFmpegCore packages a particular sequence
of checks, execution policy and evidence for supported tasks. That is an
inference about developer effort from the cited interfaces, not proof of a
unique technical capability or superior safety, speed, codec breadth, or
popularity. PyFFmpegCore still depends on an installed FFmpeg build and is not
a sandbox for hostile media.

The [research notes](https://github.com/OthmaneBlial/pyffmpegcore/tree/main/research_pyffmpegcore_comparison_2026_09_19)
record the exact primary sources and separate documented facts from these
positioning inferences. Recheck them when adjacent projects release new APIs.
