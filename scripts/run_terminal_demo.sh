#!/usr/bin/env bash
set -euo pipefail

demo_version="${PYFFMPEGCORE_DEMO_VERSION:?Set PYFFMPEGCORE_DEMO_VERSION to the public release version.}"
demo_cli="demo-env/bin/pyffmpegcore"

pause_after() {
  sleep "$1"
}

show_command() {
  printf '\n\033[1;36m$ %s\033[0m\n' "$1"
  sleep 1
}

printf '\033[1;35mPyFFmpegCore %s — public artifact to privacy-safe proof\033[0m\n' "$demo_version"
printf 'Everything below runs now in this terminal; the media is synthetic and stays local.\n'
pause_after 6

show_command "python3 -m venv demo-env"
python3 -m venv demo-env
pause_after 2

show_command "demo-env/bin/python -m pip install pyffmpegcore==$demo_version"
demo-env/bin/python -m pip install --disable-pip-version-check "pyffmpegcore==$demo_version"
pause_after 4

show_command "$demo_cli --version"
"$demo_cli" --version
pause_after 3

show_command "$demo_cli doctor"
"$demo_cli" doctor
pause_after 4

show_command "$demo_cli smoke-test --keep-dir media"
"$demo_cli" smoke-test --keep-dir media
pause_after 4

printf '\nMake the one-second synthetic input longer so structured progress is visible.\n'
show_command "ffmpeg -stream_loop 59 -i media/synthetic-input.mp4 -t 60 -c copy media/demo-input.mp4"
ffmpeg -hide_banner -loglevel error \
  -stream_loop 59 -i media/synthetic-input.mp4 -t 60 -c copy media/demo-input.mp4
pause_after 3

show_command "$demo_cli profile run web/mp4-compatible --input media/demo-input.mp4 --output media/web.mp4 --explain"
"$demo_cli" profile run web/mp4-compatible \
  --input media/demo-input.mp4 \
  --output media/web.mp4 \
  --explain
pause_after 6

show_command "$demo_cli profile run web/mp4-compatible --input media/demo-input.mp4 --output media/web.mp4 --receipt media/web.receipt.json"
"$demo_cli" profile run web/mp4-compatible \
  --input media/demo-input.mp4 \
  --output media/web.mp4 \
  --receipt media/web.receipt.json
pause_after 6

show_command "$demo_cli receipt validate media/web.receipt.json"
"$demo_cli" receipt validate media/web.receipt.json
pause_after 4

printf '\n\033[1;32mPASS\033[0m — public install, preflight, plan, progress, output, and receipt all verified.\n'
printf 'No upload. No telemetry. Content hashing stayed off.\n'
pause_after 4
printf 'Recording complete — replay the commands against any local media file.\n'
