# @othmaneblial/pyffmpegcore

Node.js launcher for the existing PyFFmpegCore CLI. The npm package adds no
transcoding runtime: install Python PyFFmpegCore and FFmpeg separately.

```bash
python -m pip install pyffmpegcore
npm install --global @othmaneblial/pyffmpegcore
pyffmpegcore-npm doctor
pyffmpegcore-npm profile run web/mp4-compatible \
  --input camera.mov --output web.mp4 --explain
```

Requires Node.js 18+, Python 3.10–3.14, and `ffmpeg`/`ffprobe` on `PATH`. The
Python CLI provides the planner, capability checks, execution, and receipts. See the
[main documentation](https://othmaneblial.github.io/pyffmpegcore/) and
[Python package on PyPI](https://pypi.org/project/pyffmpegcore/).
