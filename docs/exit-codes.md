# Exit codes

The CLI keeps these categories stable for shell and CI automation.

| Code | Category | Meaning |
| --- | --- | --- |
| `0` | Success | The requested operation completed. |
| `2` | Usage | Argparse syntax is invalid or a command group is incomplete. |
| `3` | Environment | FFmpeg or FFprobe is missing or cannot be started. |
| `4` | Validation | An input, typed option, path, or overwrite policy is invalid. |
| `5` | Processing | A valid job started but FFmpeg/FFprobe failed. |
| `6` | Partial success | A batch completed with both successes and failures. |

Human diagnostics go to stderr for errors. JSON-producing commands write their document to stdout so automation can parse it independently.
