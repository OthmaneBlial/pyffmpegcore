# Support

PyFFmpegCore is maintained as an open-source project without a guaranteed
response time. During active maintenance, issues are triaged at least weekly;
the target is an initial response within seven calendar days and a first review
of a focused pull request within fourteen. Security reports follow the shorter
private response window in `SECURITY.md`.

Before asking for help:

1. Run `pyffmpegcore doctor --json`.
2. Run `pyffmpegcore smoke-test`.
3. Check [CLI_HELP.md](CLI_HELP.md), [EXAMPLES.md](EXAMPLES.md), and [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).
4. Reduce the problem to a synthetic or redistribution-safe media sample.

Use a GitHub issue only for a reproducible bug or a concrete recipe request. Include the command, exit code, stderr, relevant `doctor` output, and whether raw FFmpeg succeeds. Remove file paths, URL credentials, personal metadata, and other secrets before posting.

Use Discussions for a completed-workflow show-and-tell or a recipe idea that is
not ready for the structured request form. Include what you completed, the
input/output contract, time to first result, and the friction you encountered.
Requests for stars, generic promotion, and unrelated FFmpeg support are closed
or redirected so the surface remains maintainable.

If maintainer capacity cannot meet the targets above, the README and Discussions
welcome post will state a maintenance pause. New `help wanted` issues and broad
promotion stop during a pause; existing security reporting remains open.

General FFmpeg usage questions belong in an FFmpeg community unless the problem is specific to PyFFmpegCore. Security reports must follow [SECURITY.md](SECURITY.md) and must not be posted publicly.
