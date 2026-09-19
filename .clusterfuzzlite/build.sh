#!/bin/bash
set -euo pipefail

fuzzer_source="$SRC/pyffmpegcore/fuzz_targets/parser_fuzzer.py"
test -f "$fuzzer_source"

PYTHONPATH="$SRC/pyffmpegcore${PYTHONPATH:+:$PYTHONPATH}" \
  pyinstaller \
    --distpath "$OUT" \
    --workpath "$WORK/pyinstaller" \
    --specpath "$WORK/pyinstaller" \
    --onefile \
    --name parser_fuzzer_package \
    "$fuzzer_source"

cat > "$OUT/parser_fuzzer" <<'EOF'
#!/bin/sh
# LLVMFuzzerTestOneInput for fuzzer detection.
set -eu
this_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$this_dir/parser_fuzzer_package" "$@"
EOF
chmod +x "$OUT/parser_fuzzer"
