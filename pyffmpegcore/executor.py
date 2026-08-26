"""Policy-aware execution of deterministic FFmpeg plans."""

from __future__ import annotations

import os
import re
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


def _legacy_progress_event(line: str, sequence: int, item: str) -> ProgressEvent | None:
    """Parse stable fields from legacy FFmpeg stderr stats without depending on column order."""
    frame_match = re.search(r"\bframe=\s*(\d+)", line)
    time_match = re.search(r"\btime=\s*([\d:.]+)", line)
    speed_match = re.search(r"\bspeed=\s*([\d.]+)x", line)
    if frame_match is None and time_match is None:
        return None
    return ProgressEvent(
        sequence=sequence,
        status="running",
        frame=int(frame_match.group(1)) if frame_match else None,
        time_seconds=_time_seconds(time_match.group(1)) if time_match else None,
        speed=float(speed_match.group(1)) if speed_match else None,
        item=item,
    )


def _without_structured_progress(command: list[str]) -> list[str]:
    fallback = []
    index = 0
    while index < len(command):
        if command[index : index + 2] == ["-progress", "pipe:1"]:
            index += 2
            continue
        if command[index] == "-nostats":
            index += 1
            continue
        fallback.append(command[index])
        index += 1
    return fallback


def _progress_protocol_unavailable(stderr: str) -> bool:
    lowered = stderr.casefold()
    return any(
        marker in lowered
        for marker in (
            "unrecognized option 'progress'",
            'unrecognized option "progress"',
            "option progress not found",
            "unknown option 'progress'",
        )
    )


@dataclass(slots=True)
class _StepOutcome:
    command: tuple[str, ...]
    returncode: int | None
    status: JobStatus
    category: str
    stdout: str
    stderr: str
    progress: ProgressEvent | None
    fallback_used: bool = False


def _terminate(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _run_step_once(
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
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError as exc:
        return _StepOutcome(tuple(command), None, JobStatus.FAILED, "environment", "", str(exc), None)

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
        for line in stream:
            stderr_lines.append(line)
            if structured:
                continue
            event = _legacy_progress_event(line, len(progress_events) + 1, name)
            if event is None:
                continue
            progress_events.append(event)
            if progress_callback is not None:
                try:
                    progress_callback(event)
                except Exception as exc:  # callbacks must not corrupt the media job
                    callback_errors.append(f"progress callback failed: {exc}")

    assert process.stdout is not None
    assert process.stderr is not None
    stdout_thread = threading.Thread(target=read_stdout, args=(process.stdout,), daemon=True)
    stderr_thread = threading.Thread(target=read_stderr, args=(process.stderr,), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    status = JobStatus.FAILED
    category = "runtime"
    try:
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
    except KeyboardInterrupt:
        _terminate(process)
        status = JobStatus.CANCELLED
        category = "cancelled"

    stdout_thread.join(timeout=2)
    stderr_thread.join(timeout=2)
    if status is JobStatus.SUCCEEDED and not structured and progress_events:
        last = progress_events[-1]
        end = ProgressEvent(
            sequence=last.sequence + 1,
            status="end",
            frame=last.frame,
            time_seconds=last.time_seconds,
            speed=last.speed,
            item=name,
        )
        progress_events.append(end)
        if progress_callback is not None:
            try:
                progress_callback(end)
            except Exception as exc:  # callbacks must not corrupt the media job
                callback_errors.append(f"progress callback failed: {exc}")
    if category == "cancelled" and not stderr_lines:
        stderr_lines.append("Job cancelled by caller.\n")
    elif category == "timeout" and not stderr_lines:
        stderr_lines.append("Job exceeded its configured timeout.\n")
    if callback_errors:
        stderr_lines.extend(f"{message}{os.linesep}" for message in callback_errors)
    return _StepOutcome(
        tuple(command),
        process.returncode,
        status,
        category,
        "".join(stdout_lines),
        "".join(stderr_lines),
        progress_events[-1] if progress_events else None,
    )


def _run_step(
    command: list[str],
    *,
    name: str,
    deadline: float | None,
    cancellation: threading.Event | None,
    progress_callback: Callable[[ProgressEvent], None] | None,
) -> _StepOutcome:
    """Prefer FFmpeg's structured protocol and retry only an explicit unsupported-option failure."""
    outcome = _run_step_once(
        command,
        name=name,
        deadline=deadline,
        cancellation=cancellation,
        progress_callback=progress_callback,
    )
    if not (
        _uses_structured_progress(command)
        and outcome.status is JobStatus.FAILED
        and outcome.category == "runtime"
        and _progress_protocol_unavailable(outcome.stderr)
    ):
        return outcome

    fallback = _run_step_once(
        _without_structured_progress(command),
        name=name,
        deadline=deadline,
        cancellation=cancellation,
        progress_callback=progress_callback,
    )
    fallback.stderr = (
        outcome.stderr
        + os.linesep
        + "Structured FFmpeg progress is unavailable; retried with legacy stderr progress."
        + os.linesep
        + fallback.stderr
    )
    fallback.fallback_used = True
    return fallback


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

        preexisting_outputs = {value for value in plan.outputs if Path(value).exists()}

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
                if (
                    command
                    and command[0].endswith(("ffmpeg", "ffmpeg.exe"))
                    and "-n" not in command
                    and "-y" not in command
                ):
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
                last_command = outcome.command
                returncode = outcome.returncode
                status = outcome.status
                category = outcome.category
                stdout_parts.append(outcome.stdout)
                stderr_parts.append(outcome.stderr)
                last_progress = outcome.progress or last_progress
                if outcome.fallback_used:
                    warnings.append("Structured FFmpeg progress unavailable; used legacy stderr fallback.")
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

        if status is not JobStatus.SUCCEEDED:
            removed_outputs = []
            for value in plan.outputs:
                path = Path(value)
                if value not in preexisting_outputs and path.is_file():
                    try:
                        path.unlink()
                    except OSError as exc:
                        warnings.append(f"Unable to remove incomplete output {path}: {exc}")
                    else:
                        removed_outputs.append(str(path))
            if removed_outputs:
                warnings.append(f"Removed incomplete outputs: {', '.join(removed_outputs)}")

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
