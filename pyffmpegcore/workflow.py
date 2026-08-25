"""Public plan -> preflight -> execution orchestration for shared workflows."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .domain import ExecutionPlan, JobResult, JobStatus, ProgressEvent
from .planning import WorkflowPlanner
from .preflight import PreflightEngine, PreflightReport
from .runner import FFmpegRunner


@dataclass(frozen=True, slots=True)
class PreparedWorkflow:
    """An immutable plan paired with its non-mutating preflight facts."""

    plan: ExecutionPlan
    preflight: PreflightReport


@dataclass(frozen=True, slots=True)
class WorkflowExecution:
    """Preflight and execution facts for one input/output item."""

    input: str | None
    output: str | None
    preflight: PreflightReport
    result: JobResult

    @property
    def succeeded(self) -> bool:
        return self.result.succeeded

    def to_dict(self) -> dict[str, object]:
        return {
            "input": self.input,
            "output": self.output,
            "preflight": self.preflight.to_dict(),
            "result": self.result.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class WorkflowBatch:
    """Versioned machine-readable outcome for a single or multi-item plan."""

    prepared: PreparedWorkflow
    items: tuple[WorkflowExecution, ...]
    schema_version: str = "1.0"

    @property
    def succeeded_count(self) -> int:
        return sum(item.succeeded for item in self.items)

    @property
    def failed_count(self) -> int:
        return len(self.items) - self.succeeded_count

    @property
    def succeeded(self) -> bool:
        return self.failed_count == 0

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


def _preflight_failure_result(plan: ExecutionPlan, report: PreflightReport) -> JobResult:
    environment_failure = any(
        check.status == "fail"
        and (check.name == "ffmpeg" or (check.name.startswith("probe/") and "was not found" in check.message))
        for check in report.checks
    )
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
        exit_category="environment" if environment_failure else "validation",
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


class WorkflowEngine:
    """Compile, preflight, and execute every supported workflow through one public layer."""

    def __init__(self, *, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        self.planner = WorkflowPlanner(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)
        self._preflight = PreflightEngine(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)

    def prepare(self, plan: ExecutionPlan) -> PreparedWorkflow:
        """Preflight an already compiled plan without mutating media or output paths."""
        return PreparedWorkflow(plan=plan, preflight=self._preflight.check(plan))

    def run(
        self,
        plan: ExecutionPlan | PreparedWorkflow,
        *,
        cancellation: threading.Event | None = None,
        progress_callback: Callable[[ProgressEvent], None] | None = None,
    ) -> WorkflowBatch:
        """Execute a single workflow or an item-aware image batch with stable results."""
        prepared = plan if isinstance(plan, PreparedWorkflow) else self.prepare(plan)
        execution_plan = prepared.plan
        if not execution_plan.workflow.startswith("images/"):
            result = (
                FFmpegRunner().execute_plan(
                    execution_plan,
                    cancellation=cancellation,
                    progress_callback=progress_callback,
                )
                if prepared.preflight.ok
                else _preflight_failure_result(execution_plan, prepared.preflight)
            )
            item = WorkflowExecution(
                input=execution_plan.inputs[0] if execution_plan.inputs else None,
                output=execution_plan.outputs[0] if execution_plan.outputs else None,
                preflight=prepared.preflight,
                result=result,
            )
            return WorkflowBatch(prepared=prepared, items=(item,))

        if not (len(execution_plan.execution_steps) == len(execution_plan.inputs) == len(execution_plan.outputs)):
            raise ValueError("image batch plan must contain one step, input, and output per item")
        items = []
        for index in range(len(execution_plan.inputs)):
            item_plan = _image_item_plan(execution_plan, index)
            preflight = self._preflight.check(item_plan)
            result = (
                FFmpegRunner().execute_plan(
                    item_plan,
                    cancellation=cancellation,
                    progress_callback=progress_callback,
                )
                if preflight.ok
                else _preflight_failure_result(item_plan, preflight)
            )
            items.append(
                WorkflowExecution(
                    input=item_plan.inputs[0],
                    output=item_plan.outputs[0],
                    preflight=preflight,
                    result=result,
                )
            )
        return WorkflowBatch(prepared=prepared, items=tuple(items))
