# Receipts that help debug without requiring private media

A useful failure report needs more than stderr: it needs the plan, preflight,
tool versions, stream summary, elapsed result, warnings, and output proof. It
does not need a user's directory tree, URL credentials, query tokens, or media
content.

PyFFmpegCore receipt schema `1.0` therefore applies these defaults:

- media paths become basename-only `<path>/file.ext` values, including parent
  directories mentioned inside preflight facts;
- URL user information and queries are redacted;
- authorization, password, token, secret, and API-key assignments are redacted;
- content hashes are disabled unless `--hash-content` explicitly opts in;
- the JSON can be validated offline without opening the media.

```bash
pyffmpegcore profile run web/mp4-compatible \
  --input private.mov --output web.mp4 \
  --receipt run.receipt.json
pyffmpegcore receipt validate run.receipt.json --json
pyffmpegcore receipt bug-report run.receipt.json --output bug-report.json
```

Redaction is defense in depth, not permission to publish blindly. Users should
inspect a receipt before sharing it, especially when raw FFmpeg metadata or a
future custom workflow can contain unusual strings. The adversarial tests in
`tests/test_receipt.py` lock credentials, embedded assignments, URLs, paths,
parent-directory messages, and opt-in hashing behavior.
