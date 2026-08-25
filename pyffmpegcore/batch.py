"""Bounded, resumable mixed-media batch execution with stable JSON contracts."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from collections.abc import Callable, Iterable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit

from .domain import ExecutionPlan
from .errors import ValidationError
from .planning import WorkflowPlanner, parse_size
from .profiles import ProfileRegistry
from .receipt import ReceiptBuilder, redact_receipt_value
from .workflow import WorkflowBatch, WorkflowEngine, WorkflowExecution

BATCH_SCHEMA_VERSION = "1.0"
BATCH_STATE_SCHEMA_VERSION = "1.0"
_TRANSIENT_DIAGNOSTICS = (
    "resource temporarily unavailable",
    "device or resource busy",
    "connection reset",
    "connection refused",
    "connection timed out",
    "temporary failure",
    "http error 500",
    "http error 502",
    "http error 503",
    "http error 504",
)
_JOB_FIELDS = {"id", "profile", "input", "output", "subtitle", "force"}
_POLICY_FIELDS = {"max_workers", "max_retries", "max_input_bytes", "per_job_timeout_seconds"}


class WorkflowExecutor(Protocol):
    """Small execution protocol used by the batch scheduler and its tests."""

    def prepare(self, plan: ExecutionPlan): ...

    def run(
        self,
        plan: ExecutionPlan,
        *,
        cancellation: threading.Event | None = None,
    ) -> WorkflowBatch: ...


@dataclass(frozen=True, slots=True)
class BatchPolicy:
    """Explicit concurrency, retry, input-size, and timeout limits."""

    max_workers: int = 2
    max_retries: int = 0
    max_input_bytes: int | None = None
    per_job_timeout_seconds: float | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.max_workers <= 32:
            raise ValidationError("batch max_workers must be between 1 and 32")
        if not 0 <= self.max_retries <= 10:
            raise ValidationError("batch max_retries must be between 0 and 10")
        if self.max_input_bytes is not None and self.max_input_bytes <= 0:
            raise ValidationError("batch max_input_bytes must be positive when provided")
        if self.per_job_timeout_seconds is not None and self.per_job_timeout_seconds <= 0:
            raise ValidationError("batch per_job_timeout_seconds must be positive when provided")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BatchJob:
    """One stable job identity paired with an immutable typed plan."""

    id: str
    plan: ExecutionPlan

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", self.id):
            raise ValidationError("batch job ids must use 1-80 letters, numbers, dots, underscores, or hyphens")

    @property
    def signature(self) -> str:
        payload = json.dumps(self.plan.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class BatchEvent:
    """One privacy-redacted JSON Lines event emitted by a batch run."""

    sequence: int
    event: str
    job_id: str
    attempt: int
    detail: str | None = None
    schema_version: str = BATCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        return redact_receipt_value(asdict(self))


@dataclass(frozen=True, slots=True)
class BatchItemOutcome:
    """Stable per-item result, including resumed and cancelled jobs."""

    job_id: str
    signature: str
    status: str
    attempts: int
    execution: WorkflowExecution | None = None
    receipt: str | None = None
    detail: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status in {"succeeded", "resumed"}

    def to_dict(self) -> dict[str, object]:
        return redact_receipt_value(
            {
                "job_id": self.job_id,
                "signature": self.signature,
                "status": self.status,
                "attempts": self.attempts,
                "execution": self.execution.to_dict() if self.execution else None,
                "receipt": self.receipt,
                "detail": self.detail,
            }
        )


@dataclass(frozen=True, slots=True)
class BatchRun:
    """Versioned ordered outcome for one bounded batch execution."""

    policy: BatchPolicy
    items: tuple[BatchItemOutcome, ...]
    schema_version: str = BATCH_SCHEMA_VERSION

    @property
    def succeeded_count(self) -> int:
        return sum(item.succeeded for item in self.items)

    @property
    def failed_count(self) -> int:
        return sum(item.status == "failed" for item in self.items)

    @property
    def cancelled_count(self) -> int:
        return sum(item.status == "cancelled" for item in self.items)

    @property
    def resumed_count(self) -> int:
        return sum(item.status == "resumed" for item in self.items)

    @property
    def succeeded(self) -> bool:
        return self.succeeded_count == len(self.items)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy": self.policy.to_dict(),
            "items": [item.to_dict() for item in self.items],
            "summary": {
                "total": len(self.items),
                "succeeded": self.succeeded_count,
                "failed": self.failed_count,
                "cancelled": self.cancelled_count,
                "resumed": self.resumed_count,
            },
        }


def is_transient_failure(execution: WorkflowExecution) -> bool:
    """Classify only documented runtime transport/resource failures as retryable."""
    if execution.result.exit_category != "runtime":
        return False
    diagnostic = f"{execution.result.stderr or ''}\n{execution.result.stdout or ''}".casefold()
    return any(marker in diagnostic for marker in _TRANSIENT_DIAGNOSTICS)


def _normalized_collision_key(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme and parsed.scheme != "file":
        return value.casefold()
    return str(Path(parsed.path if parsed.scheme == "file" else value).resolve()).casefold()


def validate_batch_jobs(jobs: Iterable[BatchJob], policy: BatchPolicy) -> tuple[BatchJob, ...]:
    """Reject duplicate identities, output collisions, duplicate work, and oversized inputs."""
    ordered = tuple(jobs)
    if not ordered:
        raise ValidationError("batch must contain at least one job")
    ids: set[str] = set()
    signatures: set[str] = set()
    outputs: dict[str, str] = {}
    for job in ordered:
        if job.id in ids:
            raise ValidationError(f"duplicate batch job id: {job.id}")
        ids.add(job.id)
        if job.signature in signatures:
            raise ValidationError(f"duplicate batch work detected for job: {job.id}")
        signatures.add(job.signature)
        for output in job.plan.outputs:
            key = _normalized_collision_key(output)
            if key in outputs:
                raise ValidationError(f"batch output collision between {outputs[key]} and {job.id}: {output}")
            outputs[key] = job.id
        if policy.max_input_bytes is not None:
            for input_value in job.plan.inputs:
                input_path = Path(input_value)
                if input_path.is_file() and input_path.stat().st_size > policy.max_input_bytes:
                    raise ValidationError(
                        f"batch input exceeds max_input_bytes for {job.id}: "
                        f"{input_path.stat().st_size} > {policy.max_input_bytes}"
                    )
    return ordered


def _load_state(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"unable to read batch state: {exc}") from exc
    if not isinstance(document, dict) or document.get("schema_version") != BATCH_STATE_SCHEMA_VERSION:
        raise ValidationError(f"batch state schema_version must be {BATCH_STATE_SCHEMA_VERSION!r}")
    completed = document.get("completed")
    if not isinstance(completed, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in completed.items()
    ):
        raise ValidationError("batch state completed must be an object of job signatures")
    return dict(completed)


def _write_state(path: Path | None, completed: dict[str, str]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(
            {"schema_version": BATCH_STATE_SCHEMA_VERSION, "completed": dict(sorted(completed.items()))},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


class BatchRunner:
    """Execute validated jobs concurrently with receipts, events, retry, and resume."""

    def __init__(
        self,
        *,
        engine: WorkflowExecutor | None = None,
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
    ) -> None:
        self.engine = engine or WorkflowEngine(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def run(
        self,
        jobs: Iterable[BatchJob],
        *,
        policy: BatchPolicy | None = None,
        cancellation: threading.Event | None = None,
        event_callback: Callable[[BatchEvent], None] | None = None,
        state_path: str | Path | None = None,
        resume: bool = False,
        receipt_dir: str | Path | None = None,
        hash_content: bool = False,
    ) -> BatchRun:
        """Run jobs once, retry transient failures, and persist successful signatures atomically."""
        selected_policy = policy or BatchPolicy()
        ordered = validate_batch_jobs(jobs, selected_policy)
        cancel = cancellation or threading.Event()
        state = Path(state_path) if state_path is not None else None
        completed = _load_state(state) if resume else {}
        receipts = Path(receipt_dir) if receipt_dir is not None else None
        if receipts is not None:
            receipts.mkdir(parents=True, exist_ok=True)
        lock = threading.Lock()
        sequence = 0

        def emit(event: str, job: BatchJob, attempt: int, detail: str | None = None) -> None:
            nonlocal sequence
            if event_callback is None:
                return
            with lock:
                sequence += 1
                item = BatchEvent(sequence=sequence, event=event, job_id=job.id, attempt=attempt, detail=detail)
                event_callback(item)

        def persist(job: BatchJob) -> None:
            with lock:
                completed[job.id] = job.signature
                _write_state(state, completed)

        def execute(job: BatchJob) -> BatchItemOutcome:
            if cancel.is_set():
                emit("cancelled", job, 0, "batch cancellation requested before execution")
                return BatchItemOutcome(job.id, job.signature, "cancelled", 0, detail="batch cancellation requested")
            if (
                resume
                and completed.get(job.id) == job.signature
                and all(Path(output).is_file() for output in job.plan.outputs)
            ):
                emit("resumed", job, 0, "matching successful state and outputs found")
                return BatchItemOutcome(job.id, job.signature, "resumed", 0)

            attempts = 0
            while attempts <= selected_policy.max_retries:
                attempts += 1
                emit("started", job, attempts)
                batch = self.engine.run(job.plan, cancellation=cancel)
                execution = batch.items[0]
                receipt_path = None
                if receipts is not None:
                    receipt_path = receipts / f"{job.id}.receipt.json"
                    ReceiptBuilder(ffmpeg_path=self.ffmpeg_path, ffprobe_path=self.ffprobe_path).build(
                        batch,
                        hash_content=hash_content,
                    ).write(receipt_path)
                if execution.succeeded:
                    persist(job)
                    emit("succeeded", job, attempts)
                    return BatchItemOutcome(
                        job.id,
                        job.signature,
                        "succeeded",
                        attempts,
                        execution=execution,
                        receipt=str(receipt_path) if receipt_path else None,
                    )
                if cancel.is_set() or execution.result.status.value == "cancelled":
                    emit("cancelled", job, attempts, execution.result.stderr)
                    return BatchItemOutcome(
                        job.id,
                        job.signature,
                        "cancelled",
                        attempts,
                        execution=execution,
                        receipt=str(receipt_path) if receipt_path else None,
                        detail=execution.result.stderr,
                    )
                if attempts <= selected_policy.max_retries and is_transient_failure(execution):
                    emit("retrying", job, attempts, "classified transient runtime failure")
                    continue
                emit("failed", job, attempts, execution.result.stderr)
                return BatchItemOutcome(
                    job.id,
                    job.signature,
                    "failed",
                    attempts,
                    execution=execution,
                    receipt=str(receipt_path) if receipt_path else None,
                    detail=execution.result.stderr,
                )
            raise AssertionError("unreachable batch retry state")

        outcomes: dict[str, BatchItemOutcome] = {}
        futures: dict[Future[BatchItemOutcome], BatchJob] = {}
        try:
            with ThreadPoolExecutor(
                max_workers=selected_policy.max_workers,
                thread_name_prefix="pyffmpegcore-batch",
            ) as pool:
                for job in ordered:
                    emit("queued", job, 0)
                    futures[pool.submit(execute, job)] = job
                for future in as_completed(futures):
                    outcomes[futures[future].id] = future.result()
        except KeyboardInterrupt:
            cancel.set()
            for future, job in futures.items():
                if future.cancel():
                    outcomes[job.id] = BatchItemOutcome(
                        job.id,
                        job.signature,
                        "cancelled",
                        0,
                        detail="batch interrupted before execution",
                    )
            for future, job in futures.items():
                if job.id not in outcomes and future.done() and not future.cancelled():
                    outcomes[job.id] = future.result()

        for job in ordered:
            if job.id not in outcomes:
                outcomes[job.id] = BatchItemOutcome(
                    job.id,
                    job.signature,
                    "cancelled",
                    0,
                    detail="batch cancelled before a result was available",
                )
        return BatchRun(policy=selected_policy, items=tuple(outcomes[job.id] for job in ordered))


@dataclass(frozen=True, slots=True)
class BatchManifest:
    """Strict versioned profile-job manifest compiled through the typed planner."""

    jobs: tuple[BatchJob, ...]
    policy: BatchPolicy = field(default_factory=BatchPolicy)
    schema_version: str = BATCH_SCHEMA_VERSION

    @classmethod
    def read(
        cls,
        path: str | Path,
        *,
        planner: WorkflowPlanner | None = None,
        force: bool = False,
    ) -> BatchManifest:
        manifest_path = Path(path).resolve()
        try:
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValidationError(f"unable to read batch manifest: {exc}") from exc
        return cls.from_dict(document, base_dir=manifest_path.parent, planner=planner, force=force)

    @classmethod
    def from_dict(
        cls,
        document: Any,
        *,
        base_dir: str | Path = ".",
        planner: WorkflowPlanner | None = None,
        force: bool = False,
    ) -> BatchManifest:
        if not isinstance(document, dict):
            raise ValidationError("batch manifest must be a JSON object")
        unknown = sorted(set(document) - {"schema_version", "policy", "jobs"})
        if unknown:
            raise ValidationError(f"unknown batch manifest fields: {', '.join(unknown)}")
        if document.get("schema_version") != BATCH_SCHEMA_VERSION:
            raise ValidationError(f"batch schema_version must be {BATCH_SCHEMA_VERSION!r}")
        policy_payload = document.get("policy", {})
        if not isinstance(policy_payload, dict):
            raise ValidationError("batch policy must be an object")
        unknown_policy = sorted(set(policy_payload) - _POLICY_FIELDS)
        if unknown_policy:
            raise ValidationError(f"unknown batch policy fields: {', '.join(unknown_policy)}")
        max_workers = policy_payload.get("max_workers", 2)
        max_retries = policy_payload.get("max_retries", 0)
        timeout = policy_payload.get("per_job_timeout_seconds")
        if not isinstance(max_workers, int) or isinstance(max_workers, bool):
            raise ValidationError("batch max_workers must be an integer")
        if not isinstance(max_retries, int) or isinstance(max_retries, bool):
            raise ValidationError("batch max_retries must be an integer")
        if timeout is not None and (not isinstance(timeout, (int, float)) or isinstance(timeout, bool)):
            raise ValidationError("batch per_job_timeout_seconds must be a number")
        max_input = policy_payload.get("max_input_bytes")
        if isinstance(max_input, str):
            max_input = parse_size(max_input)
        elif max_input is not None and (not isinstance(max_input, int) or isinstance(max_input, bool)):
            raise ValidationError("batch max_input_bytes must be an integer or size string")
        policy = BatchPolicy(
            max_workers=max_workers,
            max_retries=max_retries,
            max_input_bytes=max_input,
            per_job_timeout_seconds=float(timeout) if timeout is not None else None,
        )
        jobs_payload = document.get("jobs")
        if not isinstance(jobs_payload, list) or not jobs_payload:
            raise ValidationError("batch jobs must be a non-empty array")
        selected_planner = planner or WorkflowPlanner()
        registry = ProfileRegistry()
        root = Path(base_dir).resolve()

        def resolve(value: object, field_name: str) -> str:
            if not isinstance(value, str) or not value:
                raise ValidationError(f"batch job {field_name} must be a non-empty string")
            parsed = urlsplit(value)
            if parsed.scheme and parsed.scheme != "file":
                return value
            candidate = Path(parsed.path if parsed.scheme == "file" else value)
            return str((root / candidate).resolve()) if not candidate.is_absolute() else str(candidate.resolve())

        jobs = []
        for payload in jobs_payload:
            if not isinstance(payload, dict):
                raise ValidationError("each batch job must be an object")
            unknown_job = sorted(set(payload) - _JOB_FIELDS)
            if unknown_job:
                raise ValidationError(f"unknown batch job fields: {', '.join(unknown_job)}")
            job_id = payload.get("id")
            profile = payload.get("profile")
            if not isinstance(job_id, str) or not isinstance(profile, str):
                raise ValidationError("each batch job requires string id and profile fields")
            subtitle_value = payload.get("subtitle")
            subtitle = resolve(subtitle_value, "subtitle") if subtitle_value is not None else None
            plan = registry.plan(
                profile,
                selected_planner,
                resolve(payload.get("input"), "input"),
                resolve(payload.get("output"), "output"),
                subtitle_file=subtitle,
                force=force or payload.get("force") is True,
                timeout_seconds=policy.per_job_timeout_seconds,
            )
            jobs.append(BatchJob(job_id, plan))
        validated = validate_batch_jobs(jobs, policy)
        return cls(validated, policy)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy": self.policy.to_dict(),
            "jobs": [
                {"id": job.id, "signature": job.signature, "plan": redact_receipt_value(job.plan.to_dict())}
                for job in self.jobs
            ],
        }
