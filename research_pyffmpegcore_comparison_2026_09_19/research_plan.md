# Comparison research plan — 19 September 2026

**Question:** For a developer who needs a repeatable media conversion with
preflight, an inspectable command, an output, and a receipt, when is
PyFFmpegCore the right choice compared with adjacent tools?

## Subtopics

1. FFmpeg CLI and ffmpeg-python: confirm their documented execution and graph
   construction capabilities from official docs; identify what must be built
   separately for the common scenario.
2. python-ffmpeg and ffmpegio: confirm documented synchronous/asynchronous,
   progress, stream I/O, and option surfaces from official project docs;
   avoid assuming features are absent without evidence.
3. PyAV: confirm documented packet/frame/container scope from official docs;
   explain when direct media access is more appropriate.

## Synthesis

Use primary sources only, date the comparison, and separate externally
documented capabilities from the PyFFmpegCore scenario actually replayed from
this repository. Do not claim speed or popularity advantages. Record source
URLs in each findings file, then update `docs/comparison.md` and a short
README pointer. Limit research to a few focused official pages per tool.
