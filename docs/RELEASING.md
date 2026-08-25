# Release and Recovery Procedure

Only a maintainer with repository and PyPI project control may publish a release.

## One-Time Trusted Publishing Setup

1. Create or claim the `pyffmpegcore` project on PyPI with the intended maintainer account.
2. In PyPI, add a GitHub Trusted Publisher for owner `OthmaneBlial`, repository `pyffmpegcore`, workflow `release.yml`, environment `pypi`.
3. In GitHub, protect the `pypi` environment and restrict it to protected release tags.
4. Keep the workflow permission limited to `id-token: write`; do not add a long-lived PyPI API token.

## Release Gate

1. Confirm every earlier P0 roadmap gate and all required checks are green.
2. Update `CHANGELOG.md`, compatibility notes, and the runtime version.
3. Run the Release workflow manually in dry-run mode.
4. Create a signed annotated tag matching the runtime version exactly, for example `v0.2.0`.
5. Push the tag. The workflow builds once, tests the exact wheel on the supported OS/Python anchors, attests it, publishes it through OIDC, and creates a matching GitHub Release with checksums.
6. Verify the PyPI JSON/Simple endpoints, clean `pipx install`, `--version`, `doctor`, and `smoke-test` from the public artifact.

Never rebuild or replace files for an existing version. A failed gate means fix forward with a new commit and, if any immutable artifact was already published, a new version.

## Rollback and Yanking

Python packages cannot be safely “rolled back” by replacing files. For a broken but non-malicious release:

1. yank the affected PyPI version with a concise reason;
2. mark the GitHub Release as affected without deleting evidence;
3. document the impact and workaround;
4. publish a corrected patch version through the normal pipeline.

Delete an artifact only for legal, credential, malware, or personal-data exposure where preservation causes more harm. Record the reason privately and publish a public incident note when safe.

## Deprecation

Announce a CLI/API deprecation in the changelog and user documentation before removal. Keep the old behavior for at least one feature release when security and correctness allow, provide a migration example, and use a major version for intentional incompatible public-contract changes.

## Security Fixes

Coordinate confirmed vulnerabilities in a private GitHub Security Advisory. Prepare tests and the fix on the advisory fork when needed, request a CVE when appropriate, and publish the patched release before or with disclosure. Do not expose reporter data or exploit details prematurely. Follow the response expectations in the [security policy](https://github.com/OthmaneBlial/pyffmpegcore/blob/main/SECURITY.md).
