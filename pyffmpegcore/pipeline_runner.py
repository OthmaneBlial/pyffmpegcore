"""Pipeline execution, cache keys, and resumable state."""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from . import __version__
from ._fileio import DestinationExistsError, atomic_write_text, exclusive_write_text
from .domain import is_url_like_path
from .errors import ValidationError
from .pipeline import (
    PIPELINE_STATE_SCHEMA_VERSION,
    PipelineEvent,
    PipelinePlan,
    PipelineRun,
    PipelineStepOutcome,
    PipelineStepPlan,
    _mask_secrets,
)
from .probe import FFprobeRunner
from .receipt import (
    ReceiptBuilder,
    RunReceipt,
    _prepare_receipt_paths,
    _validate_state_destination,
    redact_receipt_value,
)
from .runner import FFmpegRunner
from .workflow import WorkflowEngine

CACHE_SIGNATURE_VERSION = 2


def _file_fingerprint(path: str, content_aware: bool) -> dict[str, object]:
    parsed = urlsplit(path)
    if is_url_like_path(path) and parsed.scheme.casefold() != "file":
        return {"remote": redact_receipt_value(path)}
    candidate = Path(parsed.path if parsed.scheme.casefold() == "file" else path)
    if not candidate.is_file():
        return {"missing": candidate.name}
    stat = candidate.stat()
    if not content_aware:
        return {"name": candidate.name, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    digest = hashlib.sha256()
    with candidate.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"name": candidate.name, "size": stat.st_size, "sha256": digest.hexdigest()}


def _binary_fingerprint(binary: str) -> dict[str, object] | None:
    resolved = shutil.which(binary)
    if resolved is None:
        return None
    path = Path(resolved)
    try:
        stat = path.stat()
        return {"path": str(path.resolve()), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    except (OSError, RuntimeError):
        return None


def _cache_key(
    step: PipelineStepPlan,
    pipeline: PipelinePlan,
    runtime: dict[str, object] | None = None,
) -> str:
    payload = {
        "cache_signature_version": CACHE_SIGNATURE_VERSION,
        "plan": _mask_secrets(step.plan.to_dict(), pipeline.secret_values),
        "inputs": [_file_fingerprint(value, pipeline.cache.content_aware) for value in step.plan.inputs],
        "runtime": runtime,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _runtime_fingerprint(ffmpeg_path: str, ffprobe_path: str) -> dict[str, object] | None:
    """Identify the package, OS, and media tools that produced a cached result."""
    try:
        ffmpeg_version = FFmpegRunner(ffmpeg_path).get_version()
        ffprobe_version = FFprobeRunner(ffprobe_path).get_version()
    except (OSError, RuntimeError, subprocess.SubprocessError):
        return None
    ffmpeg_binary = _binary_fingerprint(ffmpeg_path)
    ffprobe_binary = _binary_fingerprint(ffprobe_path)
    if ffmpeg_binary is None or ffprobe_binary is None:
        return None
    return {
        "pyffmpegcore": __version__,
        "python": platform.python_version(),
        "platform": sys.platform,
        "machine": platform.machine(),
        "ffmpeg": {"version": ffmpeg_version, **ffmpeg_binary},
        "ffprobe": {"version": ffprobe_version, **ffprobe_binary},
    }


def _completed_key(
    step: PipelineStepPlan,
    pipeline: PipelinePlan,
    runtime: dict[str, object] | None,
) -> str | None:
    """Fingerprint outputs so a cache hit cannot trust mere path existence."""
    if runtime is None or any(is_url_like_path(value) for value in step.plan.inputs):
        return None
    outputs = []
    for value in step.plan.outputs:
        path = Path(value)
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
                return None
            outputs.append(_file_fingerprint(value, pipeline.cache.content_aware))
        except OSError:
            return None
    payload = {
        "cache_signature_version": CACHE_SIGNATURE_VERSION,
        "plan_inputs_and_runtime": _cache_key(step, pipeline, runtime),
        "outputs": outputs,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_pipeline_state(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"unable to read pipeline state: {exc}") from exc
    if not isinstance(document, dict) or document.get("schema_version") != PIPELINE_STATE_SCHEMA_VERSION:
        raise ValidationError(f"pipeline state schema_version must be {PIPELINE_STATE_SCHEMA_VERSION!r}")
    completed = document.get("completed")
    if not isinstance(completed, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in completed.items()
    ):
        raise ValidationError("pipeline state completed must map step ids to cache keys")
    return dict(completed)


def _write_pipeline_state(path: Path | None, completed: dict[str, str], *, overwrite: bool = True) -> None:
    if path is None:
        return
    content = json.dumps(
        {"schema_version": PIPELINE_STATE_SCHEMA_VERSION, "completed": dict(sorted(completed.items()))},
        indent=2,
    )
    writer = atomic_write_text if overwrite else exclusive_write_text
    writer(path, content + "\n")


class PipelineRunner:
    """Execute a prepared DAG with dependency blocking, cancellation, resume, and caching."""

    def __init__(self, *, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        self.engine = WorkflowEngine(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def run(
        self,
        pipeline: PipelinePlan,
        *,
        cancellation: threading.Event | None = None,
        state_path: str | Path | None = None,
        resume: bool = False,
        overwrite_state: bool = False,
        receipt_dir: str | Path | None = None,
        overwrite_receipts: bool = False,
        hash_content: bool = False,
        event_callback: Any = None,
    ) -> PipelineRun:
        """Execute steps in dependency order and return one outcome per step.

        Failed dependencies block downstream steps. Optional state supports
        resume and caching; receipts and event callbacks are opt-in. Existing
        receipts are preserved unless ``overwrite_receipts`` is enabled. State
        files are preserved unless resuming or ``overwrite_state`` is enabled,
        fresh state files are claimed before the first runnable step, and state
        files cannot alias media outputs or generated receipts.
        """
        cancel = cancellation or threading.Event()
        selected_state = Path(state_path) if state_path is not None else None
        if selected_state is None and pipeline.cache.enabled:
            selected_state = Path(pipeline.cache.directory) / f"{pipeline.name}.state.json"
        receipts = Path(receipt_dir) if receipt_dir is not None else None
        media_outputs = tuple(output for step in pipeline.steps for output in step.plan.outputs)
        allow_state_overwrite = overwrite_state or resume or (state_path is None and pipeline.cache.enabled)
        _validate_state_destination(
            selected_state,
            media_outputs,
            receipts,
            (step.id for step in pipeline.steps),
            overwrite=allow_state_overwrite,
        )
        completed = _load_pipeline_state(selected_state) if (resume or pipeline.cache.enabled) else {}
        track_cache = resume or pipeline.cache.enabled or selected_state is not None
        runtime = _runtime_fingerprint(self.ffmpeg_path, self.ffprobe_path) if track_cache else None
        receipt_paths = (
            _prepare_receipt_paths(
                receipts,
                (step.id for step in pipeline.steps),
                media_outputs,
                overwrite=overwrite_receipts,
            )
            if receipts is not None
            else {}
        )
        sequence = 0
        outcomes: dict[str, PipelineStepOutcome] = {}
        state_claimed = allow_state_overwrite or selected_state is None

        def emit(event: str, step_id: str, detail: str | None = None) -> None:
            nonlocal sequence
            if event_callback is not None:
                sequence += 1
                event_callback(PipelineEvent(sequence, event, step_id, detail))

        def claim_state_path() -> None:
            nonlocal state_claimed
            if state_claimed or selected_state is None:
                return
            try:
                _write_pipeline_state(selected_state, completed, overwrite=False)
            except DestinationExistsError as exc:
                raise ValidationError(
                    f"state file already exists: {selected_state}. Resume or explicitly allow overwrite."
                ) from exc
            except OSError as exc:
                raise ValidationError(f"unable to create state file {selected_state}: {exc}") from exc
            state_claimed = True

        for step in pipeline.steps:
            key = _cache_key(step, pipeline, runtime)
            if cancel.is_set():
                emit("cancelled", step.id, "pipeline cancellation requested")
                outcomes[step.id] = PipelineStepOutcome(step.id, "cancelled", key)
                continue
            failed_dependencies = [dependency for dependency in step.needs if not outcomes[dependency].succeeded]
            if failed_dependencies:
                detail = f"blocked by: {', '.join(failed_dependencies)}"
                emit("blocked", step.id, detail)
                outcomes[step.id] = PipelineStepOutcome(step.id, "blocked", key, detail=detail)
                continue
            key = _cache_key(step, pipeline, runtime)
            completed_key = _completed_key(step, pipeline, runtime) if (resume or pipeline.cache.enabled) else None
            if completed_key is not None and completed.get(step.id) == completed_key:
                status = "cached" if pipeline.cache.enabled else "resumed"
                emit(status, step.id)
                outcomes[step.id] = PipelineStepOutcome(step.id, status, completed_key)
                continue
            claim_state_path()
            emit("started", step.id)
            batch = self.engine.run(step.plan, cancellation=cancel)
            execution = batch.items[0]
            receipt_path = receipt_paths.get(step.id)
            if receipt_path is not None:
                raw_receipt = ReceiptBuilder(ffmpeg_path=self.ffmpeg_path, ffprobe_path=self.ffprobe_path).build(
                    batch,
                    hash_content=hash_content,
                )
                RunReceipt(_mask_secrets(raw_receipt.to_dict(), pipeline.secret_values)).write(
                    receipt_path,
                    overwrite=overwrite_receipts,
                )
            if execution.succeeded:
                completed_key = _completed_key(step, pipeline, runtime) if track_cache else None
                if completed_key is None:
                    completed.pop(step.id, None)
                else:
                    completed[step.id] = completed_key
                _write_pipeline_state(selected_state, completed)
                emit("succeeded", step.id)
                outcomes[step.id] = PipelineStepOutcome(
                    step.id,
                    "succeeded",
                    completed_key or key,
                    execution=execution,
                    receipt=str(receipt_path) if receipt_path else None,
                )
            elif cancel.is_set() or execution.result.status.value == "cancelled":
                emit("cancelled", step.id, execution.result.stderr)
                outcomes[step.id] = PipelineStepOutcome(
                    step.id,
                    "cancelled",
                    key,
                    execution=execution,
                    receipt=str(receipt_path) if receipt_path else None,
                    detail=execution.result.stderr,
                )
            else:
                emit("failed", step.id, execution.result.stderr)
                outcomes[step.id] = PipelineStepOutcome(
                    step.id,
                    "failed",
                    key,
                    execution=execution,
                    receipt=str(receipt_path) if receipt_path else None,
                    detail=execution.result.stderr,
                )
        return PipelineRun(pipeline, tuple(outcomes[step.id] for step in pipeline.steps))
