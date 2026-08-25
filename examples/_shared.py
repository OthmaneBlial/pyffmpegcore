"""Small presentation helpers shared by repository examples."""

from __future__ import annotations

from collections.abc import Callable

from pyffmpegcore import ExecutionPlan, ProgressEvent, WorkflowBatch, WorkflowEngine


def run_plan(
    engine: WorkflowEngine,
    plan: ExecutionPlan,
    *,
    progress_callback: Callable[[ProgressEvent], None] | None = None,
) -> WorkflowBatch:
    """Execute through the public workflow engine and print useful failures."""
    batch = engine.run(plan, progress_callback=progress_callback)
    for item in batch.items:
        if not item.succeeded:
            print(item.result.stderr or "FFmpeg command failed.")
    return batch


def print_progress(event: ProgressEvent) -> None:
    """Render typed progress without parsing FFmpeg stderr."""
    if event.status == "end":
        print("Progress: complete")
    elif event.time_seconds is not None:
        print(f"Progress time: {event.time_seconds:.2f}s", end="\r")
