# Architecture for contributors

PyFFmpegCore keeps FFmpeg as a system dependency. The package plans typed
workflows, checks the machine before mutation, runs managed processes, and
records what happened. The CLI, Python API, and declarative pipelines meet at
the same `ExecutionPlan` and `WorkflowPlanner`; they have different input
formats and validation rules.

| Concern | Current home | Contract to preserve |
| --- | --- | --- |
| CLI syntax and argument defaults | `cli_parser.py` | Command names, flags, help, and parsed handler names |
| Shell completion output | `cli_completion.py` | Metadata from the parser tree and the four emitted scripts |
| CLI option translation | `cli_planning.py` | One typed plan per media-writing command |
| Public workflow compilation | `planning.py`, `profiles.py` | `ExecutionPlan` fields, warnings, required capabilities, and command vector |
| Non-mutating checks | `preflight.py` | Explicit pass, warning, or failure before execution |
| Shared execution | `workflow.py`, `runner.py`, `executor.py` | Job results, overwrite policy, timeout, cancellation, and cleanup |
| Pipelines | `pipeline.py`, `pipeline_compiler.py`, `pipeline_runner.py` | Strict versioned documents, dependency order, typed plans, cache state, and redaction |
| Evidence | `receipt.py` | Versioned receipt schema and privacy defaults |

The CLI path is `cli_parser.build_parser` → `cli_planning.build_cli_plan` →
`cli_execution.prepare_cli_job` → `WorkflowEngine.prepare` →
`WorkflowEngine.run`. `cli.py` handles user-facing rendering and exit codes.
The pipeline path resolves variables and dependencies in `PipelineCompiler`,
then calls the same `WorkflowPlanner` methods used by the CLI and Python API.

The CLI and pipeline contain similar `convert`, `compress`, and profile
branches because they accept different source formats. The CLI maps flags;
the pipeline validates a restricted document schema and step options. Keep
their adapters separate unless a failing contract test demonstrates a shared
behavioral bug. Add a workflow at the typed planner first, then expose only
the input surfaces it can validate. Tests should compare normalized plans and
results across surfaces when they promise the same operation.

Changes to a public plan, result, receipt, or document schema need explicit
versioning or migration. See [API stability](api-stability.md),
[schemas](schemas.md), and the [test methodology](test-methodology.md).
