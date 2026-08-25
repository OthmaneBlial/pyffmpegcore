# GitHub Action

The repository Action runs a versioned JSON or TOML pipeline inside the
official image, then uploads its outputs and privacy-redacted execution
evidence even when the media job fails.

```yaml
jobs:
  media:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4.2.2
      - uses: OthmaneBlial/pyffmpegcore@ACTION_COMMIT_SHA
        env:
          OUTPUT_DIR: build/release
        with:
          pipeline: pipelines/web-publish.json
          environment: OUTPUT_DIR
          artifacts: build/**
```

Replace `ACTION_COMMIT_SHA` with the immutable revision documented below. A
moving branch or tag is convenient for exploration but is not a reproducible
supply-chain boundary.

## Security and evidence behavior

- The Action accepts environment **names**, never inline secret values. Only
  the requested names are passed into the container and pipeline compiler.
- The image is fixed in `action.yml` by OCI digest, networking defaults to
  `none`, and all requested paths must stay under `GITHUB_WORKSPACE`. Set
  `network: bridge` only for a pipeline that intentionally declares remote
  inputs.
- The container runs with the host runner UID/GID, so generated files remain
  usable by later workflow steps.
- Receipts, atomic resume state, JSON Lines events, the machine-readable result,
  and requested output globs are uploaded for 14 days.
- `resume: true` and `force: true` are CI-friendly defaults. Set either input to
  `false` when stricter fresh-workspace behavior is required.

The default image is
`ghcr.io/othmaneblial/pyffmpegcore@sha256:d251ae8b20430cd671f64c4007998ce31d21e503ff06f9a309c7f33f6b8dbf3e`.
The exact Action commit is filled only after the local/container/Action
receipt-parity workflow passes.
