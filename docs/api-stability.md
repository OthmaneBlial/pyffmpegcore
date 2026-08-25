# Python API stability and deprecation

PyFFmpegCore is currently beta. Public names are the symbols exported by `pyffmpegcore.__all__`; undocumented module internals remain private.

Before 1.0, an incompatible public-API change must:

1. ship a runtime `DeprecationWarning` and a migration note;
2. keep the old path working for at least two minor releases and at least 90 days;
3. identify the first version allowed to remove it;
4. include tests for both the compatibility path and its replacement.

After 1.0, public API and versioned JSON schemas follow semantic versioning. Patch releases do not remove fields or change workflow output contracts. Additive fields may appear in minor releases; consumers should ignore fields they do not understand.

Profile, plan, pipeline, and receipt schemas have independent `schema_version` fields. A schema migration command must exist before a supported version is removed.

The low-level argument-vector escape hatch remains available for advanced FFmpeg use, but it is intentionally less stable than typed workflows. It never invokes a command shell, injects overwrite refusal by default, and accepts an explicit `OverwritePolicy` when replacement is intended.
