# Container image and supply-chain policy

The supported container packages the Python CLI with a documented Debian FFmpeg
build. It runs as UID/GID `10001`, uses no shell entrypoint, and supports
`linux/amd64` and `linux/arm64`.

```bash
docker run --rm \
  ghcr.io/othmaneblial/pyffmpegcore@sha256:d251ae8b20430cd671f64c4007998ce31d21e503ff06f9a309c7f33f6b8dbf3e \
  doctor
docker run --rm \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  ghcr.io/othmaneblial/pyffmpegcore@sha256:d251ae8b20430cd671f64c4007998ce31d21e503ff06f9a309c7f33f6b8dbf3e \
  pipeline run pipeline.json --receipt-dir receipts
```

Do not use a mutable tag for repeatable automation. The digest above is the
public `linux/amd64` and `linux/arm64` index built from revision `f4f9ed8` after
the runtime and vulnerability gates passed. The repository Action uses the same
digest by default.

## Build inputs

- base: `python:3.12.14-slim-bookworm@sha256:0f5b26b9518d002b6173fd61daad821fa340635ebfec5bba471013f9ca114579`
- FFmpeg Debian package: `7:5.1.9-0+deb12u1`
- Python package: the exact checked-out repository revision recorded by OCI
  labels and provenance
- runtime user: numeric UID/GID `10001`

The base digest is immutable. Debian dependency resolution can still change
when a security update is published, so the pushed image digest, SBOM, and
provenance—not a local rebuild—are the release identity.

## Publication gate

The container workflow:

1. builds an amd64 candidate;
2. proves the non-root user, `doctor`, and synthetic smoke test;
3. blocks on fixed HIGH or CRITICAL Trivy findings;
4. publishes an amd64/arm64 OCI image only after those gates;
5. attaches BuildKit SBOM and maximum provenance;
6. creates a GitHub artifact attestation for the pushed digest.

A weekly scheduled run rebuilds and scans without publishing. Dependency or
base updates require a reviewed pull request and a new immutable digest.
Container maintenance is owned by the repository maintainer; unresolved
HIGH/CRITICAL findings block a new image rather than being silently waived.

## Licensing and codecs

PyFFmpegCore source is MIT. The container also redistributes Debian's FFmpeg
package and its transitive libraries under their own licenses, including
GPL/LGPL components. Debian copyright files remain installed under
`/usr/share/doc`, and the generated SBOM inventories the installed packages.
Codec patent rules vary by jurisdiction; image users remain responsible for
their media and deployment context.

The review baseline is the Debian Bookworm FFmpeg package source and copyright
metadata. A future custom FFmpeg build requires a fresh license, codec,
security-update, and maintenance review before it can replace this image.

## Verification

```bash
docker build --file Containerfile --tag pyffmpegcore:local .
docker run --rm pyffmpegcore:local smoke-test --json

gh attestation verify \
  oci://ghcr.io/othmaneblial/pyffmpegcore@sha256:d251ae8b20430cd671f64c4007998ce31d21e503ff06f9a309c7f33f6b8dbf3e \
  --repo OthmaneBlial/pyffmpegcore
```

The workflow's `container-evidence-*` artifact contains the doctor report,
smoke report, FFmpeg version, a complete SARIF vulnerability report, and the
filtered HIGH/CRITICAL JSON publication gate for every build.
