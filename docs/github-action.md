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
      - uses: OthmaneBlial/pyffmpegcore@3a7315d9a830a3ffcbf45dccd17c6ca45400a796
        env:
          OUTPUT_DIR: build/release
        with:
          pipeline: pipelines/web-publish.json
          environment: OUTPUT_DIR
          artifacts: build/**
```

The Action reference above is the immutable revision validated by the
[Action integration run](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35447046432).
The workflow compares local, container, and Action receipts and outputs.
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
`ghcr.io/othmaneblial/pyffmpegcore@sha256:796661ae57874f07221e9ad258499b9a9473282544744615c7b40b719aadbc9a`.
The image was verified through the
[container run](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35446437477),
and the Action integration run above compared the local, container, and Action
results on this pin. A future Action revision needs its own integration run.
