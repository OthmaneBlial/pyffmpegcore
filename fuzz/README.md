# Parser mutation corpus

`scripts/fuzz_parsers.py` mutates saved valid and invalid JSON/TOML inputs for
pipeline and profile loading, plus JSON run receipts. It exercises parsing and
validation only: it never runs FFmpeg or opens media. The default seed and
iteration count are fixed so a CI failure can be reproduced.

```bash
python scripts/fuzz_parsers.py --seed 20260919 --iterations 1000
python scripts/fuzz_parsers.py --target receipt --replay /path/to/saved-input.json
```

An unexpected exception writes the exact input and a traceback to
`fuzz-crashes/`; the CI job uploads them even when it fails. Add confirmed
regressions to the corpus and a focused test before changing a parser. A clean
bounded run demonstrates that these inputs were handled; it is not an
exhaustive security proof or a substitute for isolated testing of hostile
media. Inputs are capped at 8 KiB and CI runs two fixed seeds.

The first run found a receipt file with invalid UTF-8 that escaped as
`UnicodeDecodeError`. Its exact bytes are saved as
`corpus/receipt/invalid-utf8.json`. `RunReceipt.read` now reports
`ValidationError` for that case; `tests/test_receipt.py` keeps the regression.
