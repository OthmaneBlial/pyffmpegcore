"""Adapt parsed CLI requests to the public workflow engine."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass

from .cli_planning import build_cli_plan
from .domain import ExecutionPlan, ProgressEvent
from .preflight import PreflightReport
from .workflow import PreparedWorkflow, WorkflowBatch, WorkflowEngine, WorkflowExecution

CLIExecutionBundle = WorkflowBatch
CLIItemExecution = WorkflowExecution


@dataclass(frozen=True, slots=True)
class PreparedCLIJob:
    """A CLI plan prepared by the same public engine exposed to Python callers."""

    prepared: PreparedWorkflow
    workflow_engine: WorkflowEngine

    @property
    def plan(self) -> ExecutionPlan:
        return self.prepared.plan

    @property
    def preflight(self) -> PreflightReport:
        return self.prepared.preflight


def prepare_cli_job(args: argparse.Namespace) -> PreparedCLIJob:
    """Compile parsed CLI options once and preflight the resulting immutable plan."""
    plan = build_cli_plan(args)
    engine = WorkflowEngine(ffmpeg_path=args.ffmpeg_path, ffprobe_path=args.ffprobe_path)
    return PreparedCLIJob(prepared=engine.prepare(plan), workflow_engine=engine)


def execute_prepared_cli_job(
    prepared: PreparedCLIJob,
    *,
    progress_callback: Callable[[ProgressEvent], None] | None = None,
) -> CLIExecutionBundle:
    """Execute a CLI request through the same public engine used by examples."""
    return prepared.workflow_engine.run(prepared.prepared, progress_callback=progress_callback)
