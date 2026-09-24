"""CLI handlers for built-in profiles, batches, and declarative pipelines."""

from __future__ import annotations

import argparse
import json
import threading
from collections.abc import Sequence
from dataclasses import asdict, replace
from pathlib import Path

from ._fileio import DestinationExistsError, open_text_file, write_text_file
from ._terminal import terminal_safe_text
from .batch import BatchEvent, BatchJob, BatchManifest, BatchPolicy, BatchRun, BatchRunner, validate_batch_jobs
from .cli_common import (
    EXIT_ENVIRONMENT_ERROR,
    EXIT_OK,
    EXIT_PARTIAL_SUCCESS,
    EXIT_RUNTIME_ERROR,
    EXIT_VALIDATION_ERROR,
    CLIContext,
    build_context,
    echo,
    echo_block,
    echo_error,
)
from .cli_validation import CLIError
from .domain import TemporaryFilePolicy
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
from .presentation import render_plan_text
from .profiles import Profile, ProfileRegistry
from .receipt import _local_path_key, redact_receipt_value
from .workflow import WorkflowEngine


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
            echo_block(ctx, render_plan_text(item.plan, item.preflight, explain=bool(args.explain)))
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


def _validate_distinct_run_artifacts(
    state_path: Path | None,
    events_path: Path | None,
    receipt_dir: Path | None,
    identifiers: Sequence[str],
    media_outputs: Sequence[str],
) -> None:
    destinations: dict[str, str] = {}
    output_keys = {key for output in media_outputs if (key := _local_path_key(output)) is not None}
    for label, path in (("--state", state_path), ("--events", events_path)):
        if path is None:
            continue
        key = _local_path_key(path)
        if key is None:
            continue
        if key in output_keys:
            raise CLIError(f"{label} must not overwrite a media output: {path}")
        if key in destinations:
            raise CLIError(f"{label} and {destinations[key]} resolve to the same file; choose distinct paths.")
        destinations[key] = label
    if receipt_dir is None:
        return
    for identifier in identifiers:
        receipt_path = receipt_dir / f"{identifier}.receipt.json"
        key = _local_path_key(receipt_path)
        if key is None:
            continue
        if key in output_keys:
            raise CLIError(f"receipt for {identifier} must not overwrite a media output: {receipt_path}")
        if key in destinations:
            raise CLIError(f"{destinations[key]} collides with receipt for {identifier}: {receipt_path}")
        destinations[key] = "--receipt-dir"


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

    media_outputs = tuple(output for job in manifest.jobs for output in job.plan.outputs)
    _validate_distinct_run_artifacts(
        args.state,
        args.events,
        args.receipt_dir,
        [job.id for job in manifest.jobs],
        media_outputs,
    )
    if (
        args.events is not None
        and (args.events.exists() or args.events.is_symlink())
        and not (ctx.force or args.resume)
    ):
        raise CLIError(f"Events file already exists: {args.events}. Use --resume or --force.")
    if args.state is not None and (args.state.exists() or args.state.is_symlink()) and not (ctx.force or args.resume):
        raise CLIError(f"State file already exists: {args.state}. Use --resume or --force.")
    if args.receipt_dir is not None and args.receipt_dir.exists() and any(args.receipt_dir.iterdir()):
        if not (ctx.force or args.resume):
            raise CLIError(f"Receipt directory is not empty: {args.receipt_dir}. Use --resume or --force.")

    event_handle = None
    event_lock = threading.Lock()
    try:
        if args.events is not None:
            try:
                event_handle = open_text_file(args.events, overwrite=ctx.force or args.resume)
            except DestinationExistsError as exc:
                raise CLIError(f"Events file already exists: {args.events}. Use --resume or --force.") from exc
            except OSError as exc:
                raise CLIError(
                    f"Unable to open events file {args.events}: {exc}", exit_code=EXIT_RUNTIME_ERROR
                ) from exc

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
            overwrite_state=ctx.force or args.resume,
            receipt_dir=args.receipt_dir,
            overwrite_receipts=ctx.force or args.resume,
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
    print(terminal_safe_text(_load_cli_pipeline(args).graph(args.format), preserve_newlines=True))
    return EXIT_OK


def handle_pipeline_migrate(args: argparse.Namespace) -> int:
    """Canonicalize a validated pipeline into the requested JSON schema."""
    if (args.output.exists() or args.output.is_symlink()) and not args.force:
        raise CLIError(f"Pipeline output already exists: {args.output}. Re-run with --force.")
    source = PipelineSpec.read(args.input)
    migrated = migrate_pipeline_document(source.to_dict(), args.to)
    try:
        write_text_file(args.output, json.dumps(migrated, indent=2) + "\n", overwrite=args.force)
    except DestinationExistsError as exc:
        raise CLIError(f"Pipeline output already exists: {args.output}. Re-run with --force.") from exc
    except OSError as exc:
        raise CLIError(f"Unable to write migrated pipeline: {exc}", exit_code=EXIT_RUNTIME_ERROR) from exc
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
        echo_block(ctx, pipeline.graph("text"))
        for step in prepared.steps:
            print()
            echo(ctx, f"Step: {step.id}")
            echo_block(ctx, render_plan_text(step.plan, step.preflight, explain=bool(args.explain)))
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
                    echo_error(f"{terminal_safe_text(step.id)}: {step.preflight.render()}", preserve_newlines=True)
        return EXIT_VALIDATION_ERROR

    media_outputs = tuple(output for step in pipeline.steps for output in step.plan.outputs)
    _validate_distinct_run_artifacts(
        args.state,
        args.events,
        args.receipt_dir,
        [step.id for step in pipeline.steps],
        media_outputs,
    )
    if (
        args.events is not None
        and (args.events.exists() or args.events.is_symlink())
        and not (ctx.force or args.resume)
    ):
        raise CLIError(f"Events file already exists: {args.events}. Use --resume or --force.")
    if args.state is not None and (args.state.exists() or args.state.is_symlink()) and not (ctx.force or args.resume):
        raise CLIError(f"State file already exists: {args.state}. Use --resume or --force.")
    if args.receipt_dir is not None and args.receipt_dir.exists() and any(args.receipt_dir.iterdir()):
        if not (ctx.force or args.resume):
            raise CLIError(f"Receipt directory is not empty: {args.receipt_dir}. Use --resume or --force.")

    event_handle = None
    try:
        if args.events is not None:
            try:
                event_handle = open_text_file(args.events, overwrite=ctx.force or args.resume)
            except DestinationExistsError as exc:
                raise CLIError(f"Events file already exists: {args.events}. Use --resume or --force.") from exc
            except OSError as exc:
                raise CLIError(
                    f"Unable to open events file {args.events}: {exc}", exit_code=EXIT_RUNTIME_ERROR
                ) from exc

        def write_event(event: PipelineEvent) -> None:
            if event_handle is not None:
                event_data = asdict(event)
                if pipeline.secret_values:
                    event_data["detail"] = None
                event_handle.write(json.dumps(redact_receipt_value(event_data), ensure_ascii=False) + "\n")
                event_handle.flush()

        result = PipelineRunner(ffmpeg_path=ctx.ffmpeg_path, ffprobe_path=ctx.ffprobe_path).run(
            pipeline,
            state_path=args.state,
            resume=args.resume,
            overwrite_state=ctx.force or args.resume,
            receipt_dir=args.receipt_dir,
            overwrite_receipts=ctx.force or args.resume,
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
