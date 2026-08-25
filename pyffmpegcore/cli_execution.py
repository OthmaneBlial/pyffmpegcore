"""Prepare and execute CLI requests through the shared typed workflow engine."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .cli_planning import build_cli_plan
from .domain import ExecutionPlan, JobResult, JobStatus, ProgressEvent
from .preflight import PreflightEngine, PreflightReport
from .runner import FFmpegRunner


@dataclass(frozen=True, slots=True)
class PreparedCLIJob:
    """A deterministic plan and its cached capability-aware preflight."""

    plan: ExecutionPlan
    preflight: PreflightReport
    preflight_engine: PreflightEngine


@dataclass(frozen=True, slots=True)
class CLIItemExecution:
    """Preflight and result facts for one output item."""

    input: str | None
    output: str | None
    preflight: PreflightReport
    result: JobResult

    def to_dict(self) -> dict[str, object]:
        return {
            "input": self.input,
            "output": self.output,
            "preflight": self.preflight.to_dict(),
            "result": self.result.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class CLIExecutionBundle:
    """Versioned machine-readable outcome for a CLI writing command."""

    prepared: PreparedCLIJob
    items: tuple[CLIItemExecution, ...]
    schema_version: str = "1.0"

    @property
    def succeeded_count(self) -> int:
        return sum(item.result.succeeded for item in self.items)

    @property
    def failed_count(self) -> int:
        return len(self.items) - self.succeeded_count

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "plan": self.prepared.plan.to_dict(),
            "preflight": self.prepared.preflight.to_dict(),
            "items": [item.to_dict() for item in self.items],
            "summary": {
                "total": len(self.items),
                "succeeded": self.succeeded_count,
                "failed": self.failed_count,
            },
        }


def prepare_cli_job(args: argparse.Namespace) -> PreparedCLIJob:
    """Compile parsed CLI options once and preflight the resulting immutable plan."""
    plan = build_cli_plan(args)
    engine = PreflightEngine(ffmpeg_path=args.ffmpeg_path, ffprobe_path=args.ffprobe_path)
    return PreparedCLIJob(plan=plan, preflight=engine.check(plan), preflight_engine=engine)


def _failed_preflight_result(plan: ExecutionPlan, report: PreflightReport) -> JobResult:
    environment_failure = any(
        check.status == "fail"
        and (check.name == "ffmpeg" or (check.name.startswith("probe/") and "was not found" in check.message))
        for check in report.checks
    )
    category = "environment" if environment_failure else "validation"
    outputs = tuple(
        {
            "path": value,
            "exists": Path(value).exists(),
            "size_bytes": Path(value).stat().st_size if Path(value).is_file() else None,
        }
        for value in plan.outputs
    )
    return JobResult(
        workflow=plan.workflow,
        command=plan.command,
        status=JobStatus.FAILED,
        exit_category=category,
        returncode=None,
        elapsed_seconds=0.0,
        stderr=report.render(),
        warnings=plan.warnings,
        outputs=outputs,
    )


def _image_item_plan(plan: ExecutionPlan, index: int) -> ExecutionPlan:
    step = plan.execution_steps[index]
    return ExecutionPlan(
        workflow=plan.workflow,
        command=step.command,
        inputs=(plan.inputs[index],),
        outputs=(plan.outputs[index],),
        policy=plan.policy,
        required_capabilities=plan.required_capabilities,
        selected_streams=plan.selected_streams,
        operations=plan.operations,
        warnings=plan.warnings,
        metadata={"structured_progress": True, "required_stream_types": ["video"]},
    )


def execute_prepared_cli_job(
    prepared: PreparedCLIJob,
    *,
    progress_callback: Callable[[ProgressEvent], None] | None = None,
) -> CLIExecutionBundle:
    """Execute a prepared single job or each item of an image batch."""
    plan = prepared.plan
    if not plan.workflow.startswith("images/"):
        result = (
            FFmpegRunner().execute_plan(plan, progress_callback=progress_callback)
            if prepared.preflight.ok
            else _failed_preflight_result(plan, prepared.preflight)
        )
        item = CLIItemExecution(
            input=plan.inputs[0] if plan.inputs else None,
            output=plan.outputs[0] if plan.outputs else None,
            preflight=prepared.preflight,
            result=result,
        )
        return CLIExecutionBundle(prepared=prepared, items=(item,))

    if not (len(plan.execution_steps) == len(plan.inputs) == len(plan.outputs)):
        raise ValueError("image batch plan must contain one step, input, and output per item")
    items = []
    for index in range(len(plan.inputs)):
        item_plan = _image_item_plan(plan, index)
        preflight = prepared.preflight_engine.check(item_plan)
        result = (
            FFmpegRunner().execute_plan(item_plan, progress_callback=progress_callback)
            if preflight.ok
            else _failed_preflight_result(item_plan, preflight)
        )
        items.append(
            CLIItemExecution(
                input=item_plan.inputs[0],
                output=item_plan.outputs[0],
                preflight=preflight,
                result=result,
            )
        )
    return CLIExecutionBundle(prepared=prepared, items=tuple(items))
