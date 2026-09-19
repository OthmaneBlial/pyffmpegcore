#!/bin/bash
set -euo pipefail

fuzzer_source="$SRC/pyffmpegcore/fuzz_targets/parser_fuzzer.py"
test -f "$fuzzer_source"

mkdir -p "$OUT/pyffmpegcore"
cp -R "$SRC/pyffmpegcore/pyffmpegcore" "$OUT/pyffmpegcore/"
cp "$fuzzer_source" "$OUT/pyffmpegcore/parser_fuzzer.py"

cat > "$OUT/parser_fuzzer" <<'EOF'
#!/bin/sh
set -eu
this_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHONPATH="$this_dir/pyffmpegcore${PYTHONPATH:+:$PYTHONPATH}" \
  exec python3 "$this_dir/pyffmpegcore/parser_fuzzer.py" "$@"
EOF
chmod +x "$OUT/parser_fuzzer"
