# Reviewed tool dependencies

The CI, compatibility checks, benchmark, Action integration, and release builder
install external Python tools from hash-bearing locks. They then install this
checkout without dependency resolution or build isolation; the checkout SHA is
the source boundary. `scripts/build_cli_artifacts.py` builds without a second,
unlocked build environment. The container installs its small build-tool lock
before doing the same for its local source tree, then removes those tools.

| Lock | Consumers | Inputs |
| --- | --- | --- |
| `ci.txt` | CI quality, package matrix, wheel builder, coverage, manual cold fixtures, benchmarks, Action integration, release builder | `pyproject.toml` dev extra and `tools.in` |
| `docs.txt` | CI documentation job | `pyproject.toml` dev and docs extras and `tools.in` |
| `pipx.txt` | Public PyPI installation verification | `pipx.in` |
| [`container-requirements.txt`](../../container-requirements.txt) | Container build only | `tools.in` |

The exact-wheel smoke deliberately installs the wheel through the ordinary
public dependency resolver. That checks the user installation path, including
the Python 3.10 `tomli` dependency, instead of substituting the development
lock. It records the wheel checksum and installed versions in its artifacts.
The terminal-recording helper separately hash-locks the universal `asciinema`
wheel to the [PyPI 2.4.0 file record](https://pypi.org/pypi/asciinema/2.4.0/json)
and requires a binary distribution.

Locks were generated with `uv 0.12.17` on 19 September 2026. To update them,
review the new package versions and hashes, then use:

```bash
uv pip compile pyproject.toml .github/requirements/tools.in --extra dev --universal --python-version 3.10 --generate-hashes --only-binary :all: -o .github/requirements/ci.txt
uv pip compile pyproject.toml .github/requirements/tools.in --all-extras --universal --python-version 3.10 --generate-hashes --only-binary :all: -o .github/requirements/docs.txt
uv pip compile .github/requirements/pipx.in --universal --python-version 3.10 --generate-hashes --only-binary :all: -o .github/requirements/pipx.txt
uv pip compile .github/requirements/tools.in --universal --python-version 3.12 --generate-hashes --only-binary :all: -o container-requirements.txt
```

Use `--upgrade` when deliberately refreshing versions. A lock change is ready
only after the Python 3.10–3.14 Linux package matrix, macOS/Windows wheel
smokes, docs, release dry run, and both container architecture scans pass on
the proposed SHA. A newly published image needs a new verified digest in the
Action and its integration run.
