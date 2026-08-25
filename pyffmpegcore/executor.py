"""Policy-aware execution of deterministic FFmpeg plans."""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path

from .domain import CapturePolicy, ExecutionPlan, JobResult, JobStatus, OverwritePolicy


def _captured(value: str | None, policy: CapturePolicy, tail_chars: int) -> str | None:
    if policy is CapturePolicy.DISCARD:
        return None
    value = value or ""
    return value if policy is CapturePolicy.FULL else value[-tail_chars:]


def _output_facts(paths: tuple[str, ...]) -> tuple[dict[str, object], ...]:
    facts = []
    for value in paths:
        path = Path(value)
        facts.append(
            {
                "path": str(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.is_file() else None,
            }
        )
    return tuple(facts)


class ExecutionEngine:
    """Execute argument-vector plans without invoking a command shell."""

    def execute(
        self,
        plan: ExecutionPlan,
        *,
        cancellation: threading.Event | None = None,
    ) -> JobResult:
        collision = next((value for value in plan.outputs if Path(value).exists()), None)
        if collision is not None and plan.policy.overwrite is OverwritePolicy.REFUSE:
            return JobResult(
                workflow=plan.workflow,
                command=plan.command,
                status=JobStatus.FAILED,
                exit_category="validation",
                returncode=None,
                elapsed_seconds=0.0,
                stderr=f"Output already exists: {collision}",
                warnings=plan.warnings,
                outputs=_output_facts(plan.outputs),
            )

        command = list(plan.command)
        if command and command[0].endswith(("ffmpeg", "ffmpeg.exe")):
            overwrite_flag = "-y" if plan.policy.overwrite is OverwritePolicy.REPLACE else "-n"
            command = [command[0], overwrite_flag, *command[1:]]

        started = time.monotonic()
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except FileNotFoundError:
            elapsed = time.monotonic() - started
            return JobResult(
                workflow=plan.workflow,
                command=tuple(command),
                status=JobStatus.FAILED,
                exit_category="environment",
                returncode=None,
                elapsed_seconds=elapsed,
                stderr=f"Executable not found: {command[0]}",
                warnings=plan.warnings,
                outputs=_output_facts(plan.outputs),
            )

        deadline = started + plan.policy.timeout_seconds if plan.policy.timeout_seconds is not None else None
        status = JobStatus.FAILED
        category = "runtime"
        returncode: int | None = None
        stdout = ""
        stderr = ""
        while True:
            if cancellation is not None and cancellation.is_set():
                process.terminate()
                try:
                    stdout, stderr = process.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                status = JobStatus.CANCELLED
                category = "cancelled"
                returncode = process.returncode
                break
            if deadline is not None and time.monotonic() >= deadline:
                process.terminate()
                try:
                    stdout, stderr = process.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                status = JobStatus.TIMED_OUT
                category = "timeout"
                returncode = process.returncode
                break
            try:
                stdout, stderr = process.communicate(timeout=0.1)
            except subprocess.TimeoutExpired:
                continue
            returncode = process.returncode
            status = JobStatus.SUCCEEDED if returncode == 0 else JobStatus.FAILED
            category = "ok" if returncode == 0 else "runtime"
            break

        return JobResult(
            workflow=plan.workflow,
            command=tuple(command),
            status=status,
            exit_category=category,
            returncode=returncode,
            elapsed_seconds=time.monotonic() - started,
            stdout=_captured(stdout, plan.policy.stdout, plan.policy.capture_tail_chars),
            stderr=_captured(stderr, plan.policy.stderr, plan.policy.capture_tail_chars),
            warnings=plan.warnings,
            outputs=_output_facts(plan.outputs),
        )
