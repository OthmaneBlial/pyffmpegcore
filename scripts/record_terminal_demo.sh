#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: scripts/record_terminal_demo.sh OUTPUT.cast VERSION" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_arg="$1"
demo_version="${2#v}"
output_parent="$(cd "$(dirname "$output_arg")" && pwd)"
output_path="$output_parent/$(basename "$output_arg")"

if [[ "$output_path" != *.cast ]]; then
  echo "Output must use the .cast extension: $output_path" >&2
  exit 2
fi
if [[ -e "$output_path" ]]; then
  echo "Refusing to overwrite existing recording: $output_path" >&2
  exit 2
fi

python3 "$repo_root/scripts/wait_for_pypi.py" \
  --version "$demo_version" \
  --timeout 5 \
  --interval 1

recorder_dir="$(mktemp -d /tmp/pyffmpegcore-asciinema.XXXXXX)"
capture_dir="$(mktemp -d /tmp/pyffmpegcore-terminal-demo.XXXXXX)"

cleanup() {
  case "$recorder_dir" in
    /tmp/pyffmpegcore-asciinema.*) rm -rf -- "$recorder_dir" ;;
  esac
  case "$capture_dir" in
    /tmp/pyffmpegcore-terminal-demo.*) rm -rf -- "$capture_dir" ;;
  esac
}
trap cleanup EXIT

python3 -m venv "$recorder_dir"
"$recorder_dir/bin/python" -m pip install \
  --disable-pip-version-check \
  --quiet \
  "asciinema==2.4.0"

printf -v demo_command '%q' "$repo_root/scripts/run_terminal_demo.sh"
(
  cd "$capture_dir"
  COLUMNS=100 \
    LINES=32 \
    TERM=xterm-256color \
    PYFFMPEGCORE_DEMO_VERSION="$demo_version" \
    "$recorder_dir/bin/asciinema" rec \
      --command "$demo_command" \
      --cols 100 \
      --rows 32 \
      --idle-time-limit 5 \
      --quiet \
      "$output_path"
)

python3 "$repo_root/scripts/validate_terminal_demo.py" \
  --cast "$output_path" \
  --expected-version "$demo_version" \
  --transcript "${output_path%.cast}.txt"
