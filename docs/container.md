# Container image and supply-chain policy

The supported container packages the Python CLI with a documented Debian FFmpeg
build. It runs as UID/GID `10001`, uses no shell entrypoint, and supports
`linux/amd64` and `linux/arm64`.

```bash
docker run --rm \
  ghcr.io/othmaneblial/pyffmpegcore@sha256:796661ae57874f07221e9ad258499b9a9473282544744615c7b40b719aadbc9a \
  doctor
docker run --rm \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  ghcr.io/othmaneblial/pyffmpegcore@sha256:796661ae57874f07221e9ad258499b9a9473282544744615c7b40b719aadbc9a \
  pipeline run pipeline.json --receipt-dir receipts
```

Do not use a mutable tag for repeatable automation. The digest above is the
public `linux/amd64` and `linux/arm64` index built from revision `7685c02`
in the [19 September 2026 container run](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35446437477).
Both candidate images passed the non-root runtime and blocking vulnerability
gates, including arm64 under QEMU. The repository Action uses the same digest
by default. The index and both platform manifests were retrieved anonymously
from GHCR, and `gh attestation verify` succeeded for this digest. The index
manifest bytes match its SHA-256 and list both advertised platforms.

## Build inputs

- base candidate: `python:3.12-slim-trixie@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9`
- FFmpeg Debian package candidate: `7:7.1.5-0+deb13u1`
- Python package: the exact checked-out repository revision recorded by OCI
  labels and provenance
- runtime user: numeric UID/GID `10001`

The public digest above is the immutable Bookworm image built from revision
`7685c02`. The current unpublished candidate replaces that runtime with
Trixie/FFmpeg `7:7.1.5-0+deb13u1`; its amd64/arm64 scan and smoke evidence is
recorded in [run 35449281881](https://github.com/OthmaneBlial/pyffmpegcore/actions/runs/35449281881).
It has not replaced the public digest. Debian dependency resolution can still
change when a security update is published, so the pushed image digest, SBOM,
and provenance—not a local rebuild—are the release identity.

The final runtime removes the checked-out source tree and Python packaging
tools (`pip`, `setuptools`, and `wheel`) after installing PyFFmpegCore. Those
tools are build inputs, not runtime features. CI proves their absence before
publishing an image.

## Publication gate

The container workflow:

1. builds amd64 and arm64 candidates;
2. proves the non-root user, `doctor`, and synthetic smoke test on both, using
   QEMU for arm64 on the amd64 runner;
3. blocks on HIGH or CRITICAL Trivy findings for which an upstream fix exists
   on either architecture;
4. publishes an amd64/arm64 OCI image only after those gates and an explicit
   maintainer-triggered `workflow_dispatch` with `publish=true`;
5. attaches BuildKit SBOM and maximum provenance;
6. creates a GitHub artifact attestation for the pushed digest.

The workflow is manual-only; it does not run on pushes, tags, or a schedule.
Dependency or base updates require review and a new immutable digest. A
maintainer must deliberately dispatch the workflow with `publish=true` after
reviewing the exact scan artifact.
Container maintenance is owned by the repository maintainer.

The complete SARIF also reports Debian/CPython advisories whose `Fixed Version`
is empty. The run above recorded 874 amd64 and 863 arm64 findings in the full
SARIF, and zero in each separate blocking JSON. Many findings remain open in
GitHub code scanning; passing the publication gate does not mean the image has
no vulnerabilities.
When Trivy reports a fixed HIGH or CRITICAL version, the separate blocking scan
fails until the base or package is upgraded and a new digest is published.

## Licensing and codecs

PyFFmpegCore source is MIT. The container also redistributes Debian's FFmpeg
package and its transitive libraries under their own licenses, including
GPL/LGPL components. Debian copyright files remain installed under
`/usr/share/doc`, and the generated SBOM inventories the installed packages.
Codec patent rules vary by jurisdiction; image users remain responsible for
their media and deployment context.

The public review baseline is the Debian Bookworm FFmpeg package source and
copyright metadata. The unpublished Trixie candidate uses Debian's FFmpeg
package source as well. A future custom FFmpeg build requires a fresh license,
codec, security-update, and maintenance review before it can replace this
image.

## Verification

```bash
docker build --file Containerfile --tag pyffmpegcore:local .
docker run --rm pyffmpegcore:local smoke-test --json

gh attestation verify \
  oci://ghcr.io/othmaneblial/pyffmpegcore@sha256:796661ae57874f07221e9ad258499b9a9473282544744615c7b40b719aadbc9a \
  --repo OthmaneBlial/pyffmpegcore
```

The workflow's `container-evidence-*` artifact contains the doctor report,
smoke report, FFmpeg version, complete SARIF vulnerability reports, and the
filtered HIGH/CRITICAL JSON publication gate for both architectures.
