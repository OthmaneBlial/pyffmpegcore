# Performance and overhead

PyFFmpegCore should spend time in FFmpeg, not in orchestration. The benchmark
contract compares the exact planned FFmpeg argument vector with the same job
through the CLI, then measures startup, wheel/source size, and a cold versus
cached pipeline.

```bash
python scripts/benchmark_overhead.py --repeats 5 --strict
```

The versioned JSON report records:

- median `ffmpeg -version` and `pyffmpegcore --version` startup;
- median raw versus PyFFmpegCore execution of the same thumbnail plan;
- byte-identical task intent and output sizes;
- cold pipeline time, warm cache time, and the reported cache state;
- wheel size when an artifact path is supplied;
- Python, platform, FFmpeg, CLI version, thresholds, and pass/fail facts.

The current regression gates allow at most 500 ms of startup orchestration and
one second of processing orchestration. The warm run must report `cached` and
complete faster than the cold run. These are absolute bounds because percentage
overhead on a two-second synthetic fixture exaggerates startup cost; real media
processing time is dominated by FFmpeg.

The scheduled [Benchmarks workflow](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/benchmark.yml)
publishes the complete report as an artifact. Results are environment-specific,
so the project does not claim to be faster than FFmpeg or compare unrelated
libraries using synthetic headline numbers.

The checked-in [2026-08-25 Apple Silicon baseline](https://github.com/OthmaneBlial/pyffmpegcore/blob/main/benchmarks/baseline-macos-arm64-2026-08-25.json)
recorded 89 ms median startup overhead, 501 ms orchestration around an exact
46 ms thumbnail plan, identical 9,118-byte outputs, an 84,661-byte wheel, and a
2.06x warm-cache speedup. Treat these as one machine's regression evidence, not
universal performance claims.
