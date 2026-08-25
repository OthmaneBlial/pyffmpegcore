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
      - uses: OthmaneBlial/pyffmpegcore@671a041807cdd54f7a7fed6534e7a4d69f372fb1
        env:
          OUTPUT_DIR: build/release
        with:
          pipeline: pipelines/web-publish.json
          environment: OUTPUT_DIR
          artifacts: build/**
```

The Action reference above is the immutable revision that introduced the
hardened runtime digest. The [Action integration
workflow](https://github.com/OthmaneBlial/pyffmpegcore/actions/workflows/action-integration.yml)
proves local/container/Action receipt parity whenever the Action or image
contract changes.
A moving branch or tag is convenient for exploration but is not a reproducible
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
`ghcr.io/othmaneblial/pyffmpegcore@sha256:b2ec3d7ffc054ce65a5e3470e4ffb19d15708d30e613c01e3217bb9331251458`.
The verified Action commit is
`671a041807cdd54f7a7fed6534e7a4d69f372fb1`.
