"""Policy-aware execution of deterministic FFmpeg plans."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from .domain import (
    CapturePolicy,
    ExecutionPlan,
    ExecutionStep,
    JobResult,
    JobStatus,
    OverwritePolicy,
    ProgressEvent,
    TemporaryFilePolicy,
)


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


def _concat_path(path: str) -> str:
    escaped = path.replace("\\", "/").replace("'", "'\\''")
    return f"'{escaped}'"


def _time_seconds(value: str) -> float | None:
    try:
        if ":" not in value:
            return float(value)
        hours, minutes, seconds = value.split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except (TypeError, ValueError):
        return None


def _optional_number(value: str | None, converter):
    if not value or value == "N/A":
        return None
    try:
        return converter(value)
    except (TypeError, ValueError):
        return None


def _progress_event(state: dict[str, str], sequence: int, item: str) -> ProgressEvent:
    frame = state.get("frame")
    speed = state.get("speed", "").removesuffix("x")
    time_value = state.get("out_time_us") or state.get("out_time_ms")
    if time_value and time_value != "N/A":
        microseconds = _optional_number(time_value, float)
        time_seconds = microseconds / 1_000_000 if microseconds is not None else None
    else:
        time_seconds = _time_seconds(state.get("out_time", ""))
    return ProgressEvent(
        sequence=sequence,
        status="end" if state.get("progress") == "end" else "running",
        frame=_optional_number(frame, int),
        time_seconds=time_seconds,
        speed=_optional_number(speed, float),
        item=item,
    )


def _uses_structured_progress(command: list[str]) -> bool:
    return any(command[index : index + 2] == ["-progress", "pipe:1"] for index in range(max(0, len(command) - 1)))


@dataclass(slots=True)
class _StepOutcome:
    returncode: int | None
    status: JobStatus
    category: str
    stdout: str
    stderr: str
    progress: ProgressEvent | None


def _terminate(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _run_step(
    command: list[str],
    *,
    name: str,
    deadline: float | None,
    cancellation: threading.Event | None,
    progress_callback: Callable[[ProgressEvent], None] | None,
) -> _StepOutcome:
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        return _StepOutcome(None, JobStatus.FAILED, "environment", "", str(exc), None)

    structured = _uses_structured_progress(command)
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    callback_errors: list[str] = []
    progress_state: dict[str, str] = {}
    progress_events: list[ProgressEvent] = []

    def read_stdout(stream: TextIO) -> None:
        for line in stream:
            if not structured:
                stdout_lines.append(line)
                continue
            stripped = line.strip()
            if "=" not in stripped:
                stdout_lines.append(line)
                continue
            key, value = stripped.split("=", 1)
            progress_state[key] = value
            if key != "progress":
                continue
            event = _progress_event(progress_state, len(progress_events) + 1, name)
            progress_events.append(event)
            if progress_callback is not None:
                try:
                    progress_callback(event)
                except Exception as exc:  # callbacks must not corrupt the media job
                    callback_errors.append(f"progress callback failed: {exc}")
            progress_state.clear()

    def read_stderr(stream: TextIO) -> None:
        stderr_lines.extend(stream)

    assert process.stdout is not None
    assert process.stderr is not None
    stdout_thread = threading.Thread(target=read_stdout, args=(process.stdout,), daemon=True)
    stderr_thread = threading.Thread(target=read_stderr, args=(process.stderr,), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    status = JobStatus.FAILED
    category = "runtime"
    while process.poll() is None:
        if cancellation is not None and cancellation.is_set():
            _terminate(process)
            status = JobStatus.CANCELLED
            category = "cancelled"
            break
        if deadline is not None and time.monotonic() >= deadline:
            _terminate(process)
            status = JobStatus.TIMED_OUT
            category = "timeout"
            break
        time.sleep(0.05)
    else:
        status = JobStatus.SUCCEEDED if process.returncode == 0 else JobStatus.FAILED
        category = "ok" if process.returncode == 0 else "runtime"

    stdout_thread.join(timeout=2)
    stderr_thread.join(timeout=2)
    if callback_errors:
        stderr_lines.extend(f"{message}{os.linesep}" for message in callback_errors)
    return _StepOutcome(
        process.returncode,
        status,
        category,
        "".join(stdout_lines),
        "".join(stderr_lines),
        progress_events[-1] if progress_events else None,
    )


def _materialize_steps(plan: ExecutionPlan) -> tuple[tuple[ExecutionStep, ...], Path | None]:
    steps = plan.execution_steps
    placeholders = {
        value
        for step in steps
        for argument in step.command
        for value in (
            "<pyffmpegcore-passlog>",
            "<pyffmpegcore-concat-manifest>",
            "<pyffmpegcore-subtitle-copy>",
        )
        if value in argument
    }
    if not placeholders:
        return steps, None

    workspace = Path(tempfile.mkdtemp(prefix="pyffmpegcore-run-"))
    try:
        replacements: dict[str, str] = {}
        if "<pyffmpegcore-passlog>" in placeholders:
            replacements["<pyffmpegcore-passlog>"] = str(workspace / "ffmpeg2pass")
        if "<pyffmpegcore-concat-manifest>" in placeholders:
            inputs = plan.metadata.get("concat_manifest")
            if not isinstance(inputs, list) or not all(isinstance(value, str) for value in inputs):
                raise ValueError("concat plan is missing its validated manifest inputs")
            manifest = workspace / "concat.txt"
            manifest.write_text("".join(f"file {_concat_path(value)}\n" for value in inputs), encoding="utf-8")
            replacements["<pyffmpegcore-concat-manifest>"] = str(manifest)
        if "<pyffmpegcore-subtitle-copy>" in placeholders:
            source = plan.metadata.get("subtitle_copy_source")
            if not isinstance(source, str):
                raise ValueError("subtitle plan is missing its temporary-copy source")
            subtitle = workspace / f"subtitles{Path(source).suffix}"
            shutil.copyfile(source, subtitle)
            replacements["<pyffmpegcore-subtitle-copy>"] = str(subtitle).replace("\\", "/").replace(":", "\\:")

        materialized = tuple(
            ExecutionStep(
                step.name,
                tuple(
                    next(
                        (
                            argument.replace(token, replacement)
                            for token, replacement in replacements.items()
                            if token in argument
                        ),
                        argument,
                    )
                    for argument in step.command
                ),
            )
            for step in steps
        )
        return materialized, workspace
    except Exception:
        shutil.rmtree(workspace, ignore_errors=True)
        raise


class ExecutionEngine:
    """Execute argument-vector plans without invoking a command shell."""

    def execute(
        self,
        plan: ExecutionPlan,
        *,
        cancellation: threading.Event | None = None,
        progress_callback: Callable[[ProgressEvent], None] | None = None,
    ) -> JobResult:
        executable = plan.execution_steps[0].command[0]
        explicit_executable = any(separator in executable for separator in ("/", "\\"))
        executable_available = (
            Path(executable).is_file() if explicit_executable else shutil.which(executable) is not None
        )
        if not executable_available:
            return JobResult(
                workflow=plan.workflow,
                command=plan.command,
                status=JobStatus.FAILED,
                exit_category="environment",
                returncode=None,
                elapsed_seconds=0.0,
                stderr=f"Executable not found: {executable}",
                warnings=plan.warnings,
                outputs=_output_facts(plan.outputs),
            )

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

        started = time.monotonic()
        deadline = started + plan.policy.timeout_seconds if plan.policy.timeout_seconds is not None else None
        status = JobStatus.SUCCEEDED
        category = "ok"
        returncode: int | None = None
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        last_command = plan.command
        last_progress: ProgressEvent | None = None
        workspace: Path | None = None
        warnings = list(plan.warnings)
        try:
            steps, workspace = _materialize_steps(plan)
            for output in plan.outputs:
                Path(output).parent.mkdir(parents=True, exist_ok=True)
        except (OSError, ValueError) as exc:
            if workspace is not None:
                shutil.rmtree(workspace, ignore_errors=True)
            return JobResult(
                workflow=plan.workflow,
                command=plan.command,
                status=JobStatus.FAILED,
                exit_category="validation",
                returncode=None,
                elapsed_seconds=time.monotonic() - started,
                stderr=str(exc),
                warnings=plan.warnings,
                outputs=_output_facts(plan.outputs),
            )

        try:
            for step in steps:
                command = list(step.command)
                if command and command[0].endswith(("ffmpeg", "ffmpeg.exe")):
                    overwrite_flag = "-y" if plan.policy.overwrite is OverwritePolicy.REPLACE else "-n"
                    command = [command[0], overwrite_flag, *command[1:]]
                last_command = tuple(command)
                outcome = _run_step(
                    command,
                    name=step.name,
                    deadline=deadline,
                    cancellation=cancellation,
                    progress_callback=progress_callback,
                )
                returncode = outcome.returncode
                status = outcome.status
                category = outcome.category
                stdout_parts.append(outcome.stdout)
                stderr_parts.append(outcome.stderr)
                last_progress = outcome.progress or last_progress
                if status is not JobStatus.SUCCEEDED:
                    break
        finally:
            if workspace is not None:
                retain = plan.policy.temporary_files is TemporaryFilePolicy.KEEP or (
                    plan.policy.temporary_files is TemporaryFilePolicy.KEEP_ON_ERROR
                    and status is not JobStatus.SUCCEEDED
                )
                if retain:
                    warnings.append(f"Temporary workspace retained: {workspace}")
                else:
                    shutil.rmtree(workspace, ignore_errors=True)

        return JobResult(
            workflow=plan.workflow,
            command=last_command,
            status=status,
            exit_category=category,
            returncode=returncode,
            elapsed_seconds=time.monotonic() - started,
            stdout=_captured("\n".join(stdout_parts), plan.policy.stdout, plan.policy.capture_tail_chars),
            stderr=_captured("\n".join(stderr_parts), plan.policy.stderr, plan.policy.capture_tail_chars),
            progress=last_progress,
            warnings=tuple(warnings),
            outputs=_output_facts(plan.outputs),
        )
