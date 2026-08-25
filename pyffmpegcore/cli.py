"""
Command-line entrypoint for PyFFmpegCore.
"""

from __future__ import annotations

import argparse
import json
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from . import __version__
from .batch import BatchEvent, BatchJob, BatchManifest, BatchPolicy, BatchRun, BatchRunner, validate_batch_jobs
from .capabilities import CapabilityInventory
from .cli_execution import CLIExecutionBundle, execute_prepared_cli_job, prepare_cli_job
from .cli_parser import build_parser
from .cli_planning import build_cli_plan
from .cli_validation import (
    CLIError,
    prepare_output_dir,
    prepare_output_path,
    require_existing_input,
    runtime_error_to_cli_error,
    validate_global_contract,
)
from .domain import JobResult, ProgressEvent, TemporaryFilePolicy
from .errors import ValidationError
from .pipeline import (
    PipelineCompiler,
    PipelineEvent,
    PipelinePlan,
    PipelinePreflightEngine,
    PipelineRun,
    PipelineRunner,
    PipelineSpec,
    PipelineStepPlan,
    migrate_pipeline_document,
    variables_from_environment,
)
from .planning import parse_size
from .preflight import PreflightEngine
from .presentation import render_plan_json, render_plan_text
from .probe import FFprobeRunner
from .profiles import Profile, ProfileRegistry
from .receipt import ReceiptBuilder, RunReceipt, build_bug_report, migrate_receipt
from .runner import FFmpegRunner
from .workflow import WorkflowEngine

EXIT_OK = 0
EXIT_ENVIRONMENT_ERROR = 3
EXIT_USAGE_ERROR = 2
EXIT_VALIDATION_ERROR = 4
EXIT_RUNTIME_ERROR = 5
EXIT_PARTIAL_SUCCESS = 6

WRITING_COMMANDS = frozenset(
    {
        "convert",
        "compress",
        "extract-audio",
        "thumbnail",
        "waveform",
        "speed",
        "concat",
        "subtitles",
        "mix-audio",
        "normalize-audio",
        "images",
    }
)


@dataclass
class CLIContext:
    """
    Shared execution context derived from parsed CLI arguments.
    """

    verbose: bool = False
    quiet: bool = False
    force: bool = False
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"


class CLIProgressPrinter:
    """
    Lightweight terminal progress printer for FFmpeg jobs.
    """

    def __init__(self, total_duration: float | None = None):
        self.total_duration = total_duration
        self.seen_progress = False

    def __call__(self, progress: dict[str, Any]) -> None:
        if progress.get("status") == "end":
            if self.seen_progress:
                print("\rProgress: 100% complete", file=sys.stderr)
            return

        time_seconds = progress.get("time_seconds")
        if time_seconds is not None and self.total_duration:
            self.seen_progress = True
            percentage = min(100.0, (time_seconds / self.total_duration) * 100.0)
            print(
                f"\rProgress: {percentage:5.1f}% ({time_seconds:0.2f}s)",
                end="",
                file=sys.stderr,
                flush=True,
            )
            return

        frame = progress.get("frame")
        if frame is not None:
            self.seen_progress = True
            print(
                f"\rFrame: {frame}",
                end="",
                file=sys.stderr,
                flush=True,
            )


def collect_completion_metadata(
    parser: argparse.ArgumentParser,
    path: tuple[str, ...] = (),
) -> dict[tuple[str, ...], dict[str, list[str]]]:
    """
    Collect subcommand and option metadata from an argparse tree.
    """
    metadata: dict[tuple[str, ...], dict[str, list[str]]] = {}
    options: list[str] = []
    subcommand_parsers: dict[str, argparse.ArgumentParser] = {}

    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, subparser in action.choices.items():
                subcommand_parsers[name] = subparser
            continue
        if action.option_strings and action.help != argparse.SUPPRESS:
            options.extend(action.option_strings)

    metadata[path] = {
        "options": sorted(dict.fromkeys(options)),
        "subcommands": sorted(subcommand_parsers),
    }

    for name, subparser in subcommand_parsers.items():
        metadata.update(collect_completion_metadata(subparser, path + (name,)))

    return metadata


def completion_key(path: tuple[str, ...]) -> str:
    """
    Render a shell-safe key for a parser path.
    """
    return "root" if not path else "__".join(path)


def powershell_quote(value: str) -> str:
    """
    Quote a literal string for PowerShell array output.
    """
    return "'" + value.replace("'", "''") + "'"


def render_bash_completion(program_name: str, metadata: dict[tuple[str, ...], dict[str, list[str]]]) -> str:
    """
    Render a bash completion function from parser metadata.
    """
    lines = [
        f"_{program_name}_completion() {{",
        "    local cur key",
        "    COMPREPLY=()",
        '    cur="${COMP_WORDS[COMP_CWORD]}"',
        "    key=root",
        "    for ((i=1; i<COMP_CWORD; i++)); do",
        '        case "$key:${COMP_WORDS[i]}" in',
    ]

    for path, node in metadata.items():
        key = completion_key(path)
        for subcommand in node["subcommands"]:
            next_key = completion_key(path + (subcommand,))
            lines.append(f"            {key}:{subcommand}) key={next_key} ;;")

    lines.extend(
        [
            "        esac",
            "    done",
            '    case "$key" in',
        ]
    )

    for path, node in metadata.items():
        key = completion_key(path)
        candidates = " ".join(node["subcommands"] + node["options"])
        lines.append(f'        {key}) COMPREPLY=( $(compgen -W {shlex.quote(candidates)} -- "$cur") ) ;;')

    lines.extend(
        [
            "    esac",
            "}",
            f"complete -F _{program_name}_completion {program_name}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_zsh_completion(program_name: str, metadata: dict[tuple[str, ...], dict[str, list[str]]]) -> str:
    """
    Render a zsh completion function from parser metadata.
    """
    lines = [
        f"#compdef {program_name}",
        "",
        f"_{program_name}() {{",
        '  local key="root"',
        "  local -a candidates",
        "  local word",
        "  for (( i=2; i<CURRENT; i++ )); do",
        '    word="${words[i]}"',
        '    case "$key:$word" in',
    ]

    for path, node in metadata.items():
        key = completion_key(path)
        for subcommand in node["subcommands"]:
            next_key = completion_key(path + (subcommand,))
            lines.append(f'      {key}:{subcommand}) key="{next_key}" ;;')

    lines.extend(
        [
            "    esac",
            "  done",
            '  case "$key" in',
        ]
    )

    for path, node in metadata.items():
        key = completion_key(path)
        candidates = " ".join(shlex.quote(word) for word in (node["subcommands"] + node["options"]))
        lines.append(f"    {key}) candidates=({candidates}) ;;")

    lines.extend(
        [
            "  esac",
            "  _describe 'pyffmpegcore arguments' candidates",
            "}",
            "",
            f"compdef _{program_name} {program_name}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_powershell_completion(
    program_name: str,
    metadata: dict[tuple[str, ...], dict[str, list[str]]],
) -> str:
    """
    Render a PowerShell argument completer from parser metadata.
    """
    lines = [
        f"Register-ArgumentCompleter -Native -CommandName {program_name} -ScriptBlock {{",
        "    param($wordToComplete, $commandAst, $cursorPosition)",
        "    $tokens = @($commandAst.CommandElements | Select-Object -Skip 1 | ForEach-Object { $_.Extent.Text })",
        "    if ($tokens.Count -eq 0) {",
        "        $previousTokens = @()",
        "    } elseif ($tokens.Count -eq 1) {",
        "        $previousTokens = @()",
        "    } else {",
        "        $previousTokens = $tokens[0..($tokens.Count - 2)]",
        "    }",
        '    $key = "root"',
        "    foreach ($token in $previousTokens) {",
        '        switch ("$key:$token") {',
    ]

    for path, node in metadata.items():
        key = completion_key(path)
        for subcommand in node["subcommands"]:
            next_key = completion_key(path + (subcommand,))
            lines.append(f'            "{key}:{subcommand}" {{ $key = "{next_key}"; continue }}')

    lines.extend(
        [
            "        }",
            "    }",
            "    $candidates = switch ($key) {",
        ]
    )

    for path, node in metadata.items():
        key = completion_key(path)
        candidates = ", ".join(powershell_quote(word) for word in (node["subcommands"] + node["options"]))
        lines.append(f'        "{key}" {{ @({candidates}) }}')

    lines.extend(
        [
            "    }",
            '    $candidates | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {',
            "        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)",
            "    }",
            "}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_completion_script(shell: str) -> str:
    """
    Render the requested shell completion script.
    """
    parser = build_parser()
    metadata = collect_completion_metadata(parser)
    if shell == "bash":
        return render_bash_completion("pyffmpegcore", metadata)
    if shell == "zsh":
        return render_zsh_completion("pyffmpegcore", metadata)
    if shell == "powershell":
        return render_powershell_completion("pyffmpegcore", metadata)
    raise CLIError(f"Unsupported completion shell: {shell}", exit_code=EXIT_USAGE_ERROR)


def handle_completion(args: argparse.Namespace) -> int:
    """
    Print a shell completion script to stdout.
    """
    print(render_completion_script(args.shell), end="")
    return EXIT_OK


def render_profile(ctx: CLIContext, profile: Profile) -> None:
    """Render a profile without hiding its output choices or requirements."""
    echo(ctx, f"{profile.name} v{profile.profile_version}")
    echo(ctx, profile.description)
    echo(ctx, f"Workflow: {profile.workflow}")
    echo(ctx, "Options:")
    for name, value in sorted(profile.options.items()):
        echo(ctx, f"  {name}: {value}")
    echo(ctx, "Required capabilities:")
    for capability in profile.required_capabilities:
        echo(ctx, f"  {capability}")


def handle_profile_list(args: argparse.Namespace) -> int:
    """List every maintained built-in profile."""
    profiles = ProfileRegistry().list()
    if args.json:
        print(json.dumps({"schema_version": "1.0", "profiles": [item.to_dict() for item in profiles]}, indent=2))
        return EXIT_OK
    ctx = build_context(args)
    for profile in profiles:
        echo(ctx, f"{profile.name} v{profile.profile_version} — {profile.description}")
    return EXIT_OK


def handle_profile_show(args: argparse.Namespace) -> int:
    """Show the exact choices made by one built-in profile."""
    try:
        profile = ProfileRegistry().get(args.name)
    except ValueError as exc:
        raise CLIError(str(exc)) from exc
    if args.json:
        print(json.dumps(profile.to_dict(), indent=2))
    else:
        render_profile(build_context(args), profile)
    return EXIT_OK


def handle_profile_validate(args: argparse.Namespace) -> int:
    """Validate a project or user profile without executing a media job."""
    try:
        profile = ProfileRegistry().load_file(args.path)
    except ValueError as exc:
        raise CLIError(str(exc)) from exc
    if args.json:
        print(json.dumps({"valid": True, "profile": profile.to_dict()}, indent=2))
    else:
        echo(build_context(args), f"Valid profile: {profile.name} v{profile.profile_version}")
    return EXIT_OK


def _load_cli_batch(args: argparse.Namespace) -> BatchManifest:
    """Compile a manifest and apply explicit CLI policy overrides to every typed plan."""
    ctx = build_context(args)
    manifest = BatchManifest.read(
        args.manifest,
        planner=WorkflowEngine(ffmpeg_path=ctx.ffmpeg_path, ffprobe_path=ctx.ffprobe_path).planner,
        force=ctx.force,
    )
    max_input_bytes = manifest.policy.max_input_bytes
    if getattr(args, "max_input_size", None) is not None:
        max_input_bytes = parse_size(args.max_input_size)
    timeout = getattr(args, "timeout", None)
    if timeout is None:
        timeout = manifest.policy.per_job_timeout_seconds
    policy = BatchPolicy(
        max_workers=args.max_workers if getattr(args, "max_workers", None) is not None else manifest.policy.max_workers,
        max_retries=args.max_retries if getattr(args, "max_retries", None) is not None else manifest.policy.max_retries,
        max_input_bytes=max_input_bytes,
        per_job_timeout_seconds=timeout,
    )
    temporary_files = TemporaryFilePolicy(getattr(args, "temp_files", "clean"))
    jobs = tuple(
        BatchJob(
            job.id,
            replace(
                job.plan,
                policy=replace(
                    job.plan.policy,
                    timeout_seconds=timeout,
                    temporary_files=temporary_files,
                ),
            ),
        )
        for job in manifest.jobs
    )
    return BatchManifest(validate_batch_jobs(jobs, policy), policy)


def handle_batch_validate(args: argparse.Namespace) -> int:
    """Strictly compile a batch manifest without probing or mutating media."""
    manifest = _load_cli_batch(args)
    if args.json:
        print(json.dumps({"valid": True, "manifest": manifest.to_dict()}, indent=2))
    else:
        echo(build_context(args), f"Valid batch: {len(manifest.jobs)} jobs; max_workers={manifest.policy.max_workers}")
    return EXIT_OK


def _render_batch_preview(args: argparse.Namespace, manifest: BatchManifest) -> int:
    """Preflight every batch item and render a non-mutating combined preview."""
    ctx = build_context(args)
    engine = WorkflowEngine(ffmpeg_path=ctx.ffmpeg_path, ffprobe_path=ctx.ffprobe_path)
    prepared = [(job, engine.prepare(job.plan)) for job in manifest.jobs]
    if args.plan_json:
        print(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "policy": manifest.policy.to_dict(),
                    "jobs": [
                        {
                            "id": job.id,
                            "signature": job.signature,
                            "plan": item.plan.to_dict(),
                            "preflight": item.preflight.to_dict(),
                        }
                        for job, item in prepared
                    ],
                },
                indent=2,
            )
        )
    else:
        for index, (job, item) in enumerate(prepared):
            if index:
                print()
            echo(ctx, f"Batch job: {job.id}")
            echo(ctx, render_plan_text(item.plan, item.preflight, explain=bool(args.explain)))
    return EXIT_OK if all(item.preflight.ok for _, item in prepared) else EXIT_VALIDATION_ERROR


def _batch_exit_code(result: BatchRun) -> int:
    if result.succeeded:
        return EXIT_OK
    if result.succeeded_count:
        return EXIT_PARTIAL_SUCCESS
    categories = {
        item.execution.result.exit_category
        for item in result.items
        if item.execution is not None and item.status == "failed"
    }
    if categories == {"environment"}:
        return EXIT_ENVIRONMENT_ERROR
    if categories and categories <= {"validation"}:
        return EXIT_VALIDATION_ERROR
    return EXIT_RUNTIME_ERROR


def handle_batch_run(args: argparse.Namespace) -> int:
    """Run a bounded batch and preserve machine-readable partial outcomes."""
    ctx = build_context(args)
    if getattr(args, "receipt", None) is not None:
        raise CLIError("Batch jobs require --receipt-dir so every item keeps its own receipt.", exit_code=2)
    if args.resume and args.state is None:
        raise CLIError("--resume requires --state FILE.", exit_code=2)
    manifest = _load_cli_batch(args)
    if args.dry_run or args.explain:
        return _render_batch_preview(args, manifest)

    outputs = {Path(value).resolve() for job in manifest.jobs for value in job.plan.outputs}
    for option, destination in (("--state", args.state), ("--events", args.events)):
        if destination is not None and destination.resolve() in outputs:
            raise CLIError(f"{option} must not overwrite a media output.")
    if args.events is not None and args.events.exists() and not (ctx.force or args.resume):
        raise CLIError(f"Events file already exists: {args.events}. Use --resume or --force.")
    if args.state is not None and args.state.exists() and not (ctx.force or args.resume):
        raise CLIError(f"State file already exists: {args.state}. Use --resume or --force.")
    if args.receipt_dir is not None and args.receipt_dir.exists() and any(args.receipt_dir.iterdir()):
        if not (ctx.force or args.resume):
            raise CLIError(f"Receipt directory is not empty: {args.receipt_dir}. Use --resume or --force.")

    event_handle = None
    event_lock = threading.Lock()
    try:
        if args.events is not None:
            args.events.parent.mkdir(parents=True, exist_ok=True)
            event_handle = args.events.open("w", encoding="utf-8")

        def write_event(event: BatchEvent) -> None:
            if event_handle is not None:
                with event_lock:
                    event_handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
                    event_handle.flush()

        result = BatchRunner(ffmpeg_path=ctx.ffmpeg_path, ffprobe_path=ctx.ffprobe_path).run(
            manifest.jobs,
            policy=manifest.policy,
            event_callback=write_event if event_handle is not None else None,
            state_path=args.state,
            resume=args.resume,
            receipt_dir=args.receipt_dir,
            hash_content=bool(args.hash_content),
        )
    finally:
        if event_handle is not None:
            event_handle.close()

    if args.result_json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        for item in result.items:
            if item.status == "failed":
                echo_error(f"{item.job_id}: {(item.detail or 'batch job failed').strip()}")
        echo(
            ctx,
            "Batch: "
            f"{result.succeeded_count} succeeded, {result.failed_count} failed, "
            f"{result.cancelled_count} cancelled, {result.resumed_count} resumed",
        )
    return _batch_exit_code(result)


def _load_cli_pipeline(args: argparse.Namespace) -> PipelinePlan:
    """Compile a pipeline using only named environment variables and typed workflows."""
    ctx = build_context(args)
    spec = PipelineSpec.read(args.pipeline)
    plan = PipelineCompiler(ffmpeg_path=ctx.ffmpeg_path, ffprobe_path=ctx.ffprobe_path).compile(
        spec,
        variables=variables_from_environment(getattr(args, "var", [])),
        force=ctx.force,
        timeout_seconds=getattr(args, "timeout", None),
        cache_enabled=getattr(args, "cache_enabled", None),
    )
    temporary_files = TemporaryFilePolicy(getattr(args, "temp_files", "clean"))
    return replace(
        plan,
        steps=tuple(
            PipelineStepPlan(
                step.id,
                step.needs,
                replace(step.plan, policy=replace(step.plan.policy, temporary_files=temporary_files)),
            )
            for step in plan.steps
        ),
    )


def handle_pipeline_validate(args: argparse.Namespace) -> int:
    """Strictly parse, resolve, and compile a declarative pipeline."""
    pipeline = _load_cli_pipeline(args)
    if args.json:
        # PipelinePlan.to_dict masks declared secrets; tests/test_pipeline.py covers every public renderer.
        # codeql[py/clear-text-logging-sensitive-data]
        print(json.dumps({"valid": True, "pipeline": pipeline.to_dict()}, indent=2))
    else:
        echo(build_context(args), f"Valid pipeline: {pipeline.name}; {len(pipeline.steps)} typed steps")
    return EXIT_OK


def handle_pipeline_graph(args: argparse.Namespace) -> int:
    """Render a compiled dependency graph without probing inputs."""
    # Graph output contains only validated step IDs, dependencies, workflows, and the pipeline name.
    # codeql[py/clear-text-logging-sensitive-data]
    print(_load_cli_pipeline(args).graph(args.format))
    return EXIT_OK


def handle_pipeline_migrate(args: argparse.Namespace) -> int:
    """Canonicalize a validated pipeline into the requested JSON schema."""
    if args.output.exists() and not args.force:
        raise CLIError(f"Pipeline output already exists: {args.output}. Re-run with --force.")
    source = PipelineSpec.read(args.input)
    migrated = migrate_pipeline_document(source.to_dict(), args.to)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(migrated, indent=2) + "\n", encoding="utf-8")
    echo(build_context(args), f"Migrated pipeline {source.schema_version} -> {args.to}: {args.output}")
    return EXIT_OK


def _render_pipeline_preview(args: argparse.Namespace, pipeline: PipelinePlan) -> int:
    ctx = build_context(args)
    prepared = PipelinePreflightEngine(ffmpeg_path=ctx.ffmpeg_path, ffprobe_path=ctx.ffprobe_path).prepare(
        pipeline,
        allow_existing_outputs=args.resume or pipeline.cache.enabled,
    )
    if args.plan_json:
        # PreparedPipeline.to_dict applies the same secret-value sanitizer as PipelinePlan.to_dict.
        # codeql[py/clear-text-logging-sensitive-data]
        print(json.dumps(prepared.to_dict(), indent=2))
    else:
        echo(ctx, f"Pipeline: {pipeline.name}")
        echo(ctx, pipeline.graph("text"))
        for step in prepared.steps:
            print()
            echo(ctx, f"Step: {step.id}")
            echo(ctx, render_plan_text(step.plan, step.preflight, explain=bool(args.explain)))
    return EXIT_OK if prepared.ok else EXIT_VALIDATION_ERROR


def _pipeline_exit_code(result: PipelineRun) -> int:
    if result.succeeded:
        return EXIT_OK
    if result.succeeded_count:
        return EXIT_PARTIAL_SUCCESS
    categories = {
        item.execution.result.exit_category
        for item in result.items
        if item.execution is not None and item.status == "failed"
    }
    if categories == {"environment"}:
        return EXIT_ENVIRONMENT_ERROR
    if categories and categories <= {"validation"}:
        return EXIT_VALIDATION_ERROR
    return EXIT_RUNTIME_ERROR


def handle_pipeline_run(args: argparse.Namespace) -> int:
    """Preflight the entire DAG, then run it with receipts, state, cache, and events."""
    ctx = build_context(args)
    if getattr(args, "receipt", None) is not None:
        raise CLIError("Pipeline steps require --receipt-dir so each step keeps its own receipt.", exit_code=2)
    pipeline = _load_cli_pipeline(args)
    if args.dry_run or args.explain:
        return _render_pipeline_preview(args, pipeline)
    if args.resume and args.state is None and not pipeline.cache.enabled:
        raise CLIError("--resume requires --state FILE unless pipeline caching supplies its own state.", exit_code=2)
    prepared = PipelinePreflightEngine(ffmpeg_path=ctx.ffmpeg_path, ffprobe_path=ctx.ffprobe_path).prepare(
        pipeline,
        allow_existing_outputs=args.resume or pipeline.cache.enabled,
    )
    if not prepared.ok:
        if args.result_json:
            print(json.dumps(prepared.to_dict(), indent=2))
        else:
            for step in prepared.steps:
                if not step.preflight.ok:
                    echo_error(f"{step.id}: {step.preflight.render()}")
        return EXIT_VALIDATION_ERROR

    outputs = {Path(value).resolve() for step in pipeline.steps for value in step.plan.outputs}
    for option, destination in (("--state", args.state), ("--events", args.events)):
        if destination is not None and destination.resolve() in outputs:
            raise CLIError(f"{option} must not overwrite a pipeline media output.")
    if args.events is not None and args.events.exists() and not (ctx.force or args.resume):
        raise CLIError(f"Events file already exists: {args.events}. Use --resume or --force.")
    if args.state is not None and args.state.exists() and not (ctx.force or args.resume):
        raise CLIError(f"State file already exists: {args.state}. Use --resume or --force.")
    if args.receipt_dir is not None and args.receipt_dir.exists() and any(args.receipt_dir.iterdir()):
        if not (ctx.force or args.resume):
            raise CLIError(f"Receipt directory is not empty: {args.receipt_dir}. Use --resume or --force.")

    event_handle = None
    try:
        if args.events is not None:
            args.events.parent.mkdir(parents=True, exist_ok=True)
            event_handle = args.events.open("w", encoding="utf-8")

        def write_event(event: PipelineEvent) -> None:
            if event_handle is not None:
                event_handle.write(json.dumps(event.to_dict(pipeline.secret_values), ensure_ascii=False) + "\n")
                event_handle.flush()

        result = PipelineRunner(ffmpeg_path=ctx.ffmpeg_path, ffprobe_path=ctx.ffprobe_path).run(
            pipeline,
            state_path=args.state,
            resume=args.resume,
            receipt_dir=args.receipt_dir,
            hash_content=bool(args.hash_content),
            event_callback=write_event if event_handle is not None else None,
        )
    finally:
        if event_handle is not None:
            event_handle.close()
    if args.result_json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        for item in result.items:
            if item.status in {"failed", "blocked"}:
                echo_error(f"{item.step_id}: {(item.detail or item.status).strip()}")
        echo(
            ctx,
            "Pipeline: "
            f"{result.succeeded_count} succeeded, {result.failed_count} failed, "
            f"{result.blocked_count} blocked, {result.cancelled_count} cancelled",
        )
    return _pipeline_exit_code(result)


def build_context(args: argparse.Namespace) -> CLIContext:
    """
    Build a shared CLI context from parsed arguments.
    """
    return CLIContext(
        verbose=getattr(args, "verbose", False),
        quiet=getattr(args, "quiet", False),
        force=getattr(args, "force", False),
        ffmpeg_path=getattr(args, "ffmpeg_path", "ffmpeg"),
        ffprobe_path=getattr(args, "ffprobe_path", "ffprobe"),
    )


def echo(ctx: CLIContext, message: str) -> None:
    """
    Print a human-readable message unless quiet mode is enabled.
    """
    if not ctx.quiet:
        print(message)


def echo_verbose(ctx: CLIContext, message: str) -> None:
    """
    Print diagnostic detail to stderr when verbose mode is enabled.
    """
    if ctx.verbose:
        print(f"[verbose] {message}", file=sys.stderr)


def echo_error(message: str) -> None:
    """
    Print a user-facing error message to stderr.
    """
    print(message, file=sys.stderr)


def format_bytes(byte_count: int | None) -> str:
    """
    Format byte counts into a compact human-readable string.
    """
    if byte_count is None:
        return "unknown"

    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(byte_count)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024

    return f"{byte_count} B"


def inspect_binary(binary_path: str) -> dict[str, Any]:
    """
    Inspect a binary path for existence and version information.
    """
    is_explicit_path = any(sep in binary_path for sep in ("/", "\\"))
    resolved = (
        str(Path(binary_path).resolve())
        if is_explicit_path and Path(binary_path).exists()
        else shutil.which(binary_path)
    )
    report: dict[str, Any] = {
        "requested": binary_path,
        "resolved": resolved,
        "available": False,
        "version": None,
        "error": None,
    }

    if resolved is None:
        report["error"] = f"Executable not found: {binary_path}"
        return report

    try:
        result = subprocess.run(
            [binary_path, "-version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        report["error"] = str(exc)
        return report

    if result.returncode == 0:
        report["available"] = True
        output_lines = result.stdout.splitlines()
        report["version"] = output_lines[0] if output_lines else ""
        report["configuration"] = next(
            (line.removeprefix("configuration: ") for line in output_lines if line.startswith("configuration: ")),
            None,
        )
        return report

    report["error"] = result.stderr.strip() or "Version probe failed"
    return report


def inspect_ffmpeg_capabilities(binary_path: str) -> dict[str, Any]:
    """Collect a versioned inventory used by doctor and workflow preflight."""
    return CapabilityInventory.inspect(binary_path).to_dict()


def collect_doctor_report(ctx: CLIContext) -> dict[str, Any]:
    """
    Collect environment diagnostics for the CLI.
    """
    ffmpeg = inspect_binary(ctx.ffmpeg_path)
    ffprobe = inspect_binary(ctx.ffprobe_path)
    capabilities = inspect_ffmpeg_capabilities(ctx.ffmpeg_path) if ffmpeg["available"] else None
    return {
        "cli_version": __version__,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
        },
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "capabilities": capabilities,
    }


def render_doctor_report(ctx: CLIContext, report: dict[str, Any]) -> None:
    """
    Print a human-readable diagnostics report.
    """
    platform_info = report["platform"]
    python_info = report["python"]

    echo(ctx, f"PyFFmpegCore CLI {report['cli_version']}")
    echo(ctx, f"Platform: {platform_info['system']} {platform_info['release']} ({platform_info['machine']})")
    echo(ctx, f"Python: {python_info['version']} ({python_info['executable']})")

    for label in ("ffmpeg", "ffprobe"):
        binary_report = report[label]
        if binary_report["available"]:
            echo(
                ctx,
                f"{label}: OK ({binary_report['resolved']})",
            )
            if binary_report["version"]:
                echo(ctx, f"  {binary_report['version']}")
        else:
            echo(
                ctx,
                f"{label}: MISSING ({binary_report['requested']})",
            )
            if binary_report["error"]:
                echo(ctx, f"  {binary_report['error']}")

    capabilities = report.get("capabilities")
    if capabilities:
        missing_encoders = [name for name, available in capabilities["core_encoders"].items() if not available]
        missing_filters = [name for name, available in capabilities["core_filters"].items() if not available]
        echo(
            ctx,
            "Capabilities: "
            f"{capabilities['encoder_count']} encoders, "
            f"{capabilities['decoder_count']} decoders, "
            f"{capabilities['filter_count']} filters, "
            f"{capabilities['muxer_count']} muxers, "
            f"{capabilities['demuxer_count']} demuxers",
        )
        echo(
            ctx,
            f"Protocols: {len(capabilities['input_protocols'])} input, {len(capabilities['output_protocols'])} output",
        )
        subtitle_support = capabilities["subtitle_support"]
        echo(
            ctx,
            "Subtitles: "
            f"encoders={','.join(subtitle_support['text_encoders']) or 'none'}, "
            f"burn-filter={'yes' if subtitle_support['burn_filter'] else 'no'}",
        )
        echo(ctx, f"Hardware acceleration: {', '.join(capabilities['hardware_accelerators']) or 'none reported'}")
        if missing_encoders:
            echo(ctx, f"Optional core encoders missing: {', '.join(missing_encoders)}")
        if missing_filters:
            echo(ctx, f"Optional core filters missing: {', '.join(missing_filters)}")


def handle_doctor(args: argparse.Namespace) -> int:
    """
    Run the diagnostic command.
    """
    ctx = build_context(args)
    report = collect_doctor_report(ctx)
    exit_code = EXIT_OK
    if not report["ffmpeg"]["available"] or not report["ffprobe"]["available"]:
        exit_code = EXIT_ENVIRONMENT_ERROR

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        render_doctor_report(ctx, report)

    return exit_code


def handle_receipt_validate(args: argparse.Namespace) -> int:
    """Validate a receipt schema without requiring access to the original media."""
    receipt = RunReceipt.read(args.path)
    payload = {
        "schema_version": "1.0",
        "valid": True,
        "receipt_schema_version": receipt.document["schema_version"],
        "items": len(receipt.document["items"]),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        echo(
            build_context(args),
            f"Valid receipt: schema {payload['receipt_schema_version']}, {payload['items']} item(s)",
        )
    return EXIT_OK


def handle_receipt_bug_report(args: argparse.Namespace) -> int:
    """Create a redacted doctor + receipt bundle without opening private media."""
    ctx = build_context(args)
    receipt = RunReceipt.read(args.path)
    payload = build_bug_report(receipt, collect_doctor_report(ctx))
    rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.output is None:
        print(rendered, end="")
        return EXIT_OK
    destination = prepare_output_path(str(args.output), force=ctx.force)
    try:
        destination.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        raise CLIError(f"Unable to write bug report: {exc}", exit_code=EXIT_RUNTIME_ERROR) from exc
    echo(ctx, f"Bug report: {destination}")
    return EXIT_OK


def handle_receipt_migrate(args: argparse.Namespace) -> int:
    """Canonicalize the current schema and provide an explicit future migration surface."""
    try:
        document = json.loads(args.path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CLIError(f"Unable to read receipt: {exc}") from exc
    receipt = migrate_receipt(document, args.target_version)
    if args.output is None:
        print(receipt.to_json(), end="")
        return EXIT_OK
    destination = prepare_output_path(str(args.output), force=build_context(args).force)
    try:
        receipt.write(destination)
    except OSError as exc:
        raise CLIError(f"Unable to write migrated receipt: {exc}", exit_code=EXIT_RUNTIME_ERROR) from exc
    echo(build_context(args), f"Migrated receipt: {destination}")
    return EXIT_OK


def _run_smoke_test(ctx: CLIContext, workspace: Path, retained: bool) -> dict[str, Any]:
    """
    Generate and verify a tiny local workflow without repository fixtures.
    """
    workspace.mkdir(parents=True, exist_ok=True)
    input_path = workspace / "synthetic-input.mp4"
    thumbnail_path = workspace / "synthetic-thumbnail.jpg"
    runner = FFmpegRunner(ffmpeg_path=ctx.ffmpeg_path)

    generation = runner.run(
        [
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=660:sample_rate=44100",
            "-t",
            "1",
            "-c:v",
            "mpeg4",
            "-q:v",
            "8",
            "-c:a",
            "aac",
            "-pix_fmt",
            "yuv420p",
            "-shortest",
            "-y",
            str(input_path),
        ]
    )
    raise_for_completed_process_error(generation)

    thumbnail = runner.extract_thumbnail(
        str(input_path),
        str(thumbnail_path),
        timestamp="00:00:00.200",
        width=160,
        quality=3,
    )
    raise_for_completed_process_error(thumbnail)

    probe = FFprobeRunner(ffprobe_path=ctx.ffprobe_path)
    input_metadata = probe.probe(str(input_path))
    thumbnail_metadata = probe.probe(str(thumbnail_path))
    video = input_metadata.get("video", {})
    image = thumbnail_metadata.get("video", {})
    if video.get("width") != 320 or video.get("height") != 180:
        raise CLIError("Synthetic video verification returned an unexpected resolution.")
    if image.get("width") != 160:
        raise CLIError("Synthetic thumbnail verification returned an unexpected width.")

    return {
        "schema_version": "1.0",
        "status": "ok",
        "retained": retained,
        "workspace": str(workspace.resolve()) if retained else None,
        "input": {
            "filename": input_path.name,
            "size_bytes": input_path.stat().st_size,
            "format": input_metadata.get("format_name"),
            "duration_seconds": input_metadata.get("duration"),
            "video": input_metadata.get("video"),
            "audio": input_metadata.get("audio"),
        },
        "output": {
            "filename": thumbnail_path.name,
            "size_bytes": thumbnail_path.stat().st_size,
            "image": thumbnail_metadata.get("video"),
        },
    }


def _render_smoke_report(ctx: CLIContext, report: dict[str, Any]) -> None:
    """
    Render a compact human-readable smoke-test summary.
    """
    video = report["input"]["video"]
    image = report["output"]["image"]
    echo(ctx, "Smoke test: PASS")
    echo(
        ctx,
        f"Synthetic input: {video.get('codec', 'unknown')} "
        f"{video.get('width')}x{video.get('height')} "
        f"({format_bytes(report['input']['size_bytes'])})",
    )
    echo(
        ctx,
        f"Verified thumbnail: {image.get('width')}x{image.get('height')} "
        f"({format_bytes(report['output']['size_bytes'])})",
    )
    if report["retained"]:
        echo(ctx, f"Artifacts: {report['workspace']}")
    else:
        echo(ctx, "Artifacts: cleaned up")


def handle_smoke_test(args: argparse.Namespace) -> int:
    """
    Run a package-installed synthetic end-to-end verification.
    """
    ctx = build_context(args)
    if args.keep_dir is not None:
        workspace = prepare_output_dir(str(args.keep_dir), force=ctx.force, option_name="--keep-dir")
        report = _run_smoke_test(ctx, workspace, retained=True)
    else:
        with tempfile.TemporaryDirectory(prefix="pyffmpegcore-smoke-") as temp_dir:
            report = _run_smoke_test(ctx, Path(temp_dir), retained=False)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _render_smoke_report(ctx, report)
    return EXIT_OK


def render_probe_report(ctx: CLIContext, metadata: dict[str, Any]) -> None:
    """
    Print a human-readable media summary.
    """
    echo(ctx, f"File: {metadata.get('filename', 'unknown')}")
    echo(ctx, f"Format: {metadata.get('format_long_name') or metadata.get('format_name') or 'unknown'}")
    duration = metadata.get("duration")
    if duration is not None:
        echo(ctx, f"Duration: {duration:.2f} seconds")
    if metadata.get("size") is not None:
        echo(ctx, f"Size: {metadata['size']} bytes")
    if metadata.get("bit_rate") is not None:
        echo(ctx, f"Bitrate: {metadata['bit_rate']} bps")

    video = metadata.get("video")
    if video:
        echo(ctx, "Video stream:")
        echo(ctx, f"  Codec: {video.get('codec', 'unknown')}")
        echo(ctx, f"  Resolution: {video.get('width', '?')}x{video.get('height', '?')}")
        if video.get("duration") is not None:
            echo(ctx, f"  Duration: {video['duration']}")

    audio = metadata.get("audio")
    if audio:
        echo(ctx, "Audio stream:")
        echo(ctx, f"  Codec: {audio.get('codec', 'unknown')}")
        if audio.get("sample_rate") is not None:
            echo(ctx, f"  Sample rate: {audio['sample_rate']} Hz")
        if audio.get("channels") is not None:
            echo(ctx, f"  Channels: {audio['channels']}")

    chapters = metadata.get("chapters", [])
    if chapters:
        echo(ctx, f"Chapters: {len(chapters)}")


def handle_probe(args: argparse.Namespace) -> int:
    """
    Run the probe command.
    """
    ctx = build_context(args)
    input_path = require_existing_input(args.input)

    try:
        metadata = FFprobeRunner(ffprobe_path=ctx.ffprobe_path).probe(str(input_path))
    except RuntimeError as exc:
        message = str(exc)
        exit_code = EXIT_ENVIRONMENT_ERROR if "was not found" in message else EXIT_RUNTIME_ERROR
        raise CLIError(message, exit_code=exit_code) from exc

    if args.json:
        print(json.dumps(metadata, indent=2))
    else:
        render_probe_report(ctx, metadata)

    return EXIT_OK


def raise_for_completed_process_error(result: subprocess.CompletedProcess | JobResult) -> None:
    """
    Raise a user-facing CLI error when an FFmpeg command fails.
    """
    if result.returncode == 0:
        return

    raise CLIError(result.stderr or "FFmpeg command failed.", exit_code=EXIT_RUNTIME_ERROR)


def summarize_output_file(ctx: CLIContext, output_path: Path) -> None:
    """
    Print a lightweight summary for a generated media file.
    """
    try:
        metadata = FFprobeRunner(ffprobe_path=ctx.ffprobe_path).probe(str(output_path))
    except RuntimeError:
        echo(ctx, f"Output: {output_path}")
        return

    echo(ctx, f"Output: {output_path}")
    if metadata.get("format_name"):
        echo(ctx, f"Container: {metadata['format_name']}")
    if metadata.get("duration") is not None:
        echo(ctx, f"Duration: {metadata['duration']:.2f} seconds")
    if metadata.get("size") is not None:
        echo(ctx, f"Size: {format_bytes(metadata['size'])}")
    if metadata.get("video"):
        video = metadata["video"]
        echo(ctx, f"Video: {video.get('codec', 'unknown')} {video.get('width', '?')}x{video.get('height', '?')}")
    if metadata.get("audio"):
        audio = metadata["audio"]
        echo(ctx, f"Audio: {audio.get('codec', 'unknown')}")


def build_progress_printer(ctx: CLIContext, input_path: Path) -> CLIProgressPrinter | None:
    """
    Create a progress printer when command output is not quiet.
    """
    if ctx.quiet:
        return None

    try:
        duration = FFprobeRunner(ffprobe_path=ctx.ffprobe_path).get_duration(str(input_path))
    except RuntimeError:
        duration = None

    return CLIProgressPrinter(total_duration=duration or None)


def report_batch_results(ctx: CLIContext, label: str, results: dict[str, int]) -> None:
    """
    Print a concise batch summary.
    """
    echo(
        ctx,
        (f"{label}: {results['successful']} succeeded, {results['failed']} failed, {results['total']} total"),
    )


def _execution_exit_code(bundle: CLIExecutionBundle) -> int:
    """Map stable item outcomes to the documented CLI exit categories."""
    if bundle.failed_count == 0:
        return EXIT_OK
    if bundle.succeeded_count:
        return EXIT_PARTIAL_SUCCESS
    categories = {item.result.exit_category for item in bundle.items}
    if categories == {"environment"}:
        return EXIT_ENVIRONMENT_ERROR
    if categories <= {"validation"}:
        return EXIT_VALIDATION_ERROR
    return EXIT_RUNTIME_ERROR


def _render_execution_failures(bundle: CLIExecutionBundle) -> None:
    """Write actionable item failures to stderr without corrupting JSON stdout."""
    for item in bundle.items:
        if item.result.succeeded:
            continue
        label = item.input or item.output or item.result.workflow
        diagnostic = (item.result.stderr or "FFmpeg command failed.").strip()
        echo_error(f"{label}: {diagnostic}")


def _render_execution_successes(ctx: CLIContext, bundle: CLIExecutionBundle) -> None:
    """Keep the established human summaries on top of typed results."""
    if bundle.prepared.plan.workflow.startswith("images/"):
        labels = {
            "images/convert": "Image conversion",
            "images/optimize": "Image optimization",
            "images/webp": "Image WebP conversion",
        }
        report_batch_results(
            ctx,
            labels[bundle.prepared.plan.workflow],
            {
                "total": len(bundle.items),
                "successful": bundle.succeeded_count,
                "failed": bundle.failed_count,
            },
        )
        return
    for item in bundle.items:
        if item.result.succeeded and item.output is not None:
            summarize_output_file(ctx, Path(item.output))
            proof = item.proof
            if proof["target_size_bytes"] is not None:
                status = "PASS" if proof["target_met"] else "MISS"
                echo(
                    ctx,
                    "Target-size proof: "
                    f"{format_bytes(proof['input_size_bytes'])} -> {format_bytes(proof['output_size_bytes'])}; "
                    f"limit {format_bytes(proof['target_size_bytes'])}; {status}",
                )


def handle_planned_execution(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Plan, preflight, execute, and render every media-writing CLI command."""
    prepared = prepare_cli_job(args)
    result_json = bool(getattr(args, "result_json", False))
    receipt_destination = getattr(args, "receipt", None)
    if receipt_destination is not None:
        receipt_destination = Path(receipt_destination).resolve()
        if str(receipt_destination) in prepared.plan.outputs:
            raise CLIError("--receipt must not overwrite a media output.")
        if receipt_destination.exists() and not ctx.force:
            raise CLIError(f"Receipt already exists: {receipt_destination}. Re-run with --force to overwrite.")
    progress_printer: CLIProgressPrinter | None = None
    if not ctx.quiet and not result_json and prepared.plan.inputs:
        progress_printer = build_progress_printer(ctx, Path(prepared.plan.inputs[0]))

    def report_progress(event: ProgressEvent) -> None:
        if progress_printer is not None:
            progress_printer(event.to_dict())

    bundle = execute_prepared_cli_job(
        prepared,
        progress_callback=report_progress if progress_printer is not None else None,
    )
    receipt = None
    if receipt_destination is not None:
        try:
            receipt = ReceiptBuilder(ffmpeg_path=ctx.ffmpeg_path, ffprobe_path=ctx.ffprobe_path).build(
                bundle,
                hash_content=bool(getattr(args, "hash_content", False)),
            )
            receipt.write(receipt_destination)
        except OSError as exc:
            raise CLIError(f"Unable to write receipt: {exc}", exit_code=EXIT_RUNTIME_ERROR) from exc
    if result_json:
        payload = bundle.to_dict()
        if receipt is not None:
            payload["receipt"] = {
                "schema_version": receipt.document["schema_version"],
                "path": str(receipt_destination),
            }
        print(json.dumps(payload, indent=2))
    else:
        _render_execution_failures(bundle)
        _render_execution_successes(ctx, bundle)
        if receipt is not None:
            echo(ctx, f"Receipt: {receipt_destination}")
    return _execution_exit_code(bundle)


def handle_planned_command(args: argparse.Namespace) -> int:
    """Argparse target shared by every media-writing command."""
    return handle_planned_execution(args, build_context(args))


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the CLI.
    """
    parser = build_parser()
    argv = list(argv) if argv is not None else sys.argv[1:]

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE_ERROR

    if not argv:
        parser.print_help()
        return EXIT_OK

    handler_name = getattr(args, "handler_name", "")
    handlers = {
        "handle_batch_run": handle_batch_run,
        "handle_batch_validate": handle_batch_validate,
        "handle_completion": handle_completion,
        "handle_doctor": handle_doctor,
        "handle_pipeline_graph": handle_pipeline_graph,
        "handle_pipeline_migrate": handle_pipeline_migrate,
        "handle_pipeline_run": handle_pipeline_run,
        "handle_pipeline_validate": handle_pipeline_validate,
        "handle_planned_command": handle_planned_command,
        "handle_probe": handle_probe,
        "handle_profile_list": handle_profile_list,
        "handle_profile_show": handle_profile_show,
        "handle_profile_validate": handle_profile_validate,
        "handle_receipt_bug_report": handle_receipt_bug_report,
        "handle_receipt_migrate": handle_receipt_migrate,
        "handle_receipt_validate": handle_receipt_validate,
        "handle_smoke_test": handle_smoke_test,
    }
    handler = handlers.get(handler_name) if isinstance(handler_name, str) else None
    if handler is None:
        echo_error("A complete command is required. Run `pyffmpegcore --help` for usage.")
        parser.print_usage(file=sys.stderr)
        return EXIT_USAGE_ERROR

    try:
        ctx = build_context(args)
        echo_verbose(ctx, f"command={getattr(args, 'command', None)}")
        echo_verbose(ctx, f"ffmpeg={ctx.ffmpeg_path}")
        echo_verbose(ctx, f"ffprobe={ctx.ffprobe_path}")
        preview = validate_global_contract(args, WRITING_COMMANDS)
        if getattr(args, "command", None) in {"batch", "pipeline"}:
            return int(handler(args))
        if preview:
            plan = build_cli_plan(args)
            preflight = PreflightEngine(ffmpeg_path=ctx.ffmpeg_path, ffprobe_path=ctx.ffprobe_path).check(plan)
            if args.plan_json:
                print(render_plan_json(plan, preflight))
            else:
                print(render_plan_text(plan, preflight, explain=bool(args.explain)))
            return EXIT_OK if preflight.ok else EXIT_VALIDATION_ERROR
        return int(handler(args))
    except CLIError as exc:
        echo_error(str(exc))
        return exc.exit_code
    except ValidationError as exc:
        echo_error(str(exc))
        return EXIT_VALIDATION_ERROR
    except RuntimeError as exc:
        cli_error = runtime_error_to_cli_error(exc)
        echo_error(str(cli_error))
        return cli_error.exit_code
    except ValueError as exc:
        echo_error(str(exc))
        return EXIT_VALIDATION_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
