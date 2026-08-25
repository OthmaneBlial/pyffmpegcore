# When to use PyFFmpegCore

These projects solve different problems. Feature breadth and popularity are not proof that one should replace another.

| Tool | Best fit | PyFFmpegCore difference |
| --- | --- | --- |
| Raw [FFmpeg](https://ffmpeg.org/ffmpeg.html) | Complete option surface and direct control | Adds task contracts, overwrite refusal, diagnostics, compatibility evidence, and stable automation behavior. |
| [ffmpeg-python](https://github.com/kkroening/ffmpeg-python) | Building arbitrary directed filter graphs in Python | Does not compete as a graph DSL; focuses on curated outcomes and inspectable jobs. |
| [python-ffmpeg](https://github.com/jonghwanhyeon/python-ffmpeg) | Fluent synchronous/asynchronous command construction and events | Async builders are not the headline; reproducible terminal/CI jobs are. |
| [ffmpegio](https://github.com/python-ffmpegio/python-ffmpegio) | Broad FFmpeg option access, stream I/O, and scientific/image integrations | Avoids NumPy/Pillow breadth in favor of a small task and evidence surface. |
| [PyAV](https://github.com/PyAV-Org/PyAV) | Direct in-process containers, streams, packets, codecs, and frames | Remains a subprocess task runner and does not expose low-level packet/frame control. |

Choose PyFFmpegCore when the job is one of its maintained workflows and you value deterministic validation, plans, receipts, and cross-platform proof more than arbitrary FFmpeg composition.

Choose raw FFmpeg or a neighboring library when you need features outside that contract. The low-level `FFmpegRunner.run(args)` escape hatch remains available, but callers own validation, capability checks, and media consequences for raw arguments.

Comparison reviewed: 2026-08-25. Update this page from primary project documentation when behavior changes.
