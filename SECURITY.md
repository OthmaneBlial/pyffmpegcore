# Security Policy

PyFFmpegCore executes local FFmpeg and FFprobe processes against user-supplied media. Treat media files, paths, metadata, URLs, filter arguments, and generated outputs as untrusted input.

## Supported Versions

| Version | Security fixes |
| --- | --- |
| Latest public `0.2.x` release | Yes, after it is published |
| `main` before the first public release | Best effort; not an immutable release |
| Older or unmaintained branches | No |

The [releases page](https://github.com/OthmaneBlial/pyffmpegcore/releases) is the source of truth. A source checkout from `main` is not a release and may change at any time.

## Report a Vulnerability Privately

Please use [GitHub private vulnerability reporting](https://github.com/OthmaneBlial/pyffmpegcore/security/advisories/new). Do not open a public issue for a suspected vulnerability.

Include, when safe:

- the affected version, operating system, Python version, and FFmpeg build;
- the command or Python call that triggers the problem;
- a minimal media sample or deterministic reproduction instructions;
- the expected impact and any known workaround;
- whether the report or sample contains secrets, personal data, or malicious content.

Never upload sensitive media to a public issue. Use a synthetic reproduction whenever possible.

## Response Expectations

The maintainer aims to acknowledge a complete report within three business days, provide an initial triage within seven business days, and send an update at least every fourteen days while remediation is active. These are targets, not a guaranteed service-level agreement.

Confirmed issues are coordinated privately until a fix or mitigation is ready. The release process may use a GitHub Security Advisory, a patched release, a changelog entry, and a CVE when appropriate. Disclosure timing is agreed with the reporter when possible and may be accelerated for active exploitation.

## Scope

Security-relevant areas include command construction, path/filter escaping, credential leakage in URLs or logs, unsafe temporary files, output overwrite behavior, malicious metadata, denial of service through resource exhaustion, artifact provenance, and dependency or workflow compromise.

Out of scope are vulnerabilities in FFmpeg itself, unsupported third-party wrappers, social engineering, and resource exhaustion that requires intentionally unbounded trusted input without crossing a documented limit. Reports that demonstrate a practical PyFFmpegCore amplification or unsafe default are still welcome.

See [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) for the detailed threat model.
