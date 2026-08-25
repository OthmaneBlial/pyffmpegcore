# Migration notes

## From 0.1.x source checkouts to 0.2.x

- Python 3.10 is now the minimum supported interpreter.
- Global CLI options behave consistently before or after subcommands.
- Incomplete grouped commands return usage code `2` instead of success.
- `--verbose` emits selected command and binary diagnostics.
- The package version is sourced from `pyffmpegcore.__version__`.
- Test fixtures are generated locally and the old mutable download assumptions no longer apply.
- The public release contract adds exact-artifact tests, stable quality gates, and security/release policies.

The Python API remains beta. Public incompatible changes require a changelog entry, migration example, and deprecation window when security and correctness allow.
