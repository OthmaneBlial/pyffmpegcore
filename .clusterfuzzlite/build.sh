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
    --name parser_fuzzer \
    "$fuzzer_source"
