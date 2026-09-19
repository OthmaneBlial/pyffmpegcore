# GitHub Action

The repository Action runs a versioned JSON or TOML pipeline inside the
official image, then uploads its outputs and privacy-redacted execution
evidence even when the media job fails.

```yaml
jobs:
  media:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
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
- The image is fixed in `action.yml` by OCI digest and networking defaults to
  `none`. Pipeline, receipt, state, event, result, and additional artifact paths
  must be relative to `GITHUB_WORKSPACE`; the Action rejects `..` and symlinks
  in their existing path components. Artifact globs need a literal directory
  prefix. Paths are checked before execution and again before upload. Set
  `network: bridge` only for a pipeline that intentionally declares remote
  inputs.
- Run this Action in a workspace that other untrusted processes cannot change
  concurrently. A process that replaces path components after validation can
  bypass these checks; the Action is not a filesystem sandbox.
- The container runs with the host runner UID/GID, so generated files remain
  usable by later workflow steps.
- Receipts, atomic resume state, JSON Lines events, the machine-readable result,
  and requested output globs are uploaded for 14 days.
- `resume: true` and `force: true` are CI-friendly defaults. Set either input to
  `false` when stricter fresh-workspace behavior is required.

The default image is
`ghcr.io/othmaneblial/pyffmpegcore@sha256:da8be496cc05a90226e36b11f28a5c2029475b22f0cf40fc9f228a5ea27eb8aa`.
The verified Action commit is
`671a041807cdd54f7a7fed6534e7a4d69f372fb1`.
