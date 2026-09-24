"""Public plan -> preflight -> execution orchestration for shared workflows."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TypedDict

from .domain import ExecutionPlan, JobResult, JobStatus, MediaInfo, ProgressEvent, is_url_like_path
from .planning import WorkflowPlanner
from .preflight import PreflightEngine, PreflightReport
from .probe import FFprobeRunner
from .runner import FFmpegRunner


class WorkflowProof(TypedDict):
    input_size_bytes: int | None
    output_size_bytes: int | None
    size_change_bytes: int | None
    reduction_percent: float | None
    target_size_bytes: int | None
    target_met: bool | None


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
    plan_metadata: dict[str, object] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.result.succeeded

    @property
    def proof(self) -> WorkflowProof:
        """Return measurable before/after and optional target-size facts."""
        input_size = Path(self.input).stat().st_size if self.input and Path(self.input).is_file() else None
        output_size = Path(self.output).stat().st_size if self.output and Path(self.output).is_file() else None
        target_value = self.plan_metadata.get("target_size_bytes")
        target_size = target_value if isinstance(target_value, int) and target_value > 0 else None
        reduction = None
        if input_size and output_size is not None:
            reduction = round(((input_size - output_size) / input_size) * 100, 2)
        return {
            "input_size_bytes": input_size,
            "output_size_bytes": output_size,
            "size_change_bytes": output_size - input_size
            if input_size is not None and output_size is not None
            else None,
            "reduction_percent": reduction,
            "target_size_bytes": target_size,
            "target_met": output_size <= target_size if output_size is not None and target_size is not None else None,
        }

    def to_dict(self) -> dict[str, object]:
        """Serialize item preflight, result, and measurable path/size proof."""
        return {
            "input": self.input,
            "output": self.output,
            "preflight": self.preflight.to_dict(),
            "result": self.result.to_dict(),
            "proof": self.proof,
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
        """Serialize the plan, preflight, ordered item results, and summary."""
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
        metadata={
            "structured_progress": True,
            "required_stream_types": ["video"],
            "output_contract": {"required_stream_types": ["video"]},
        },
    )


def _stream_layout(media: MediaInfo) -> tuple[tuple[str, str, str], ...]:
    """Return stable stream type/codec/language facts for preservation checks."""
    return tuple(
        sorted((stream.codec_type, stream.codec_name or "", stream.language or "") for stream in media.streams)
    )


def _verify_outputs(plan: ExecutionPlan, result: JobResult, probe: FFprobeRunner) -> JobResult:
    if not result.succeeded or not plan.outputs:
        return result

    outputs = []
    warnings = list(result.warnings)
    errors = []
    missing_probe = f"FFprobe executable '{probe.ffprobe_path}' was not found."
    verify_stream_preservation = plan.metadata.get("stream_policy") == "preserve-all"
    verify_primary_streams = plan.metadata.get("stream_policy") == "first-audio-video"
    input_layout: tuple[tuple[str, str, str], ...] | None = None
    input_primary_types: set[str] | None = None
    if verify_stream_preservation or verify_primary_streams:
        if not plan.inputs or is_url_like_path(plan.inputs[0]):
            if verify_stream_preservation:
                warnings.append("Input stream layout could not be probed; all-stream preservation is unverified.")
            else:
                warnings.append(
                    "Input primary streams could not be probed; selected-stream verification is unavailable."
                )
        else:
            try:
                input_media = probe.probe_media(plan.inputs[0])
            except (OSError, RuntimeError, ValueError):
                if verify_stream_preservation:
                    warnings.append("Input stream layout could not be probed; all-stream preservation is unverified.")
                else:
                    warnings.append(
                        "Input primary streams could not be probed; selected-stream verification is unavailable."
                    )
            else:
                if verify_stream_preservation:
                    input_layout = _stream_layout(input_media)
                else:
                    input_primary_types = {
                        stream.codec_type for stream in input_media.streams if stream.codec_type in {"audio", "video"}
                    }
    for fact in result.outputs:
        output = dict(fact)
        path = str(output["path"])
        try:
            media = probe.probe_media(path)
        except (OSError, RuntimeError, ValueError) as exc:
            reason = str(exc)
            if isinstance(exc, OSError) or reason.startswith(missing_probe):
                output["verification"] = {"status": "unavailable", "reason": reason}
                warnings.append(f"Output media could not be probed: {path}: {reason}")
            else:
                output["verification"] = {"status": "failed", "reason": reason}
                errors.append(f"Output verification failed for {path}: {reason}")
        else:
            if not media.streams:
                output["verification"] = {"status": "failed", "reason": "FFprobe found no media streams."}
                errors.append(f"Output verification failed for {path}: FFprobe found no media streams.")
            else:
                verification: dict[str, object] = {
                    "status": "probed",
                    "format_name": media.format_name,
                    "duration": media.duration,
                    "size_bytes": media.size,
                    "bit_rate": media.bit_rate,
                    "streams": [
                        {
                            "index": stream.index,
                            "type": stream.codec_type,
                            "codec": stream.codec_name,
                            "width": stream.width,
                            "height": stream.height,
                            "pixel_format": stream.details.get("pix_fmt"),
                            "sample_rate": stream.sample_rate,
                            "channels": stream.channels,
                            "language": stream.language,
                            "rotation": stream.rotation,
                        }
                        for stream in media.streams
                    ],
                    "chapter_count": len(media.chapters),
                }
                contract = plan.metadata.get("output_contract")
                contract_errors: list[str] = []
                if verify_stream_preservation:
                    output_layout = _stream_layout(media)
                    if input_layout is None:
                        verification["stream_preservation"] = {"status": "unavailable"}
                    else:
                        verification["stream_preservation"] = {
                            "status": "verified" if output_layout == input_layout else "failed",
                            "input_streams": [
                                {"type": kind, "codec": codec or None, "language": language or None}
                                for kind, codec, language in input_layout
                            ],
                            "output_streams": [
                                {"type": kind, "codec": codec or None, "language": language or None}
                                for kind, codec, language in output_layout
                            ],
                        }
                        if output_layout != input_layout:
                            expected = ", ".join("/".join(part for part in stream if part) for stream in input_layout)
                            actual = ", ".join("/".join(part for part in stream if part) for stream in output_layout)
                            contract_errors.append(
                                f"preserve-all stream layout changed: input [{expected}], output [{actual}]"
                            )
                if verify_primary_streams:
                    output_primary_types = {
                        stream.codec_type for stream in media.streams if stream.codec_type in {"audio", "video"}
                    }
                    if input_primary_types is None:
                        verification["selected_streams"] = {"status": "unavailable"}
                    else:
                        missing_types = sorted(input_primary_types - output_primary_types)
                        verification["selected_streams"] = {
                            "status": "failed" if missing_types else "verified",
                            "required_types": sorted(input_primary_types),
                            "output_types": sorted(output_primary_types),
                        }
                        contract_errors.extend(
                            f"expected output stream type '{stream_type}' from input, found none"
                            for stream_type in missing_types
                        )
                if isinstance(contract, dict):
                    expected_codecs = contract.get("codecs")
                    if isinstance(expected_codecs, dict):
                        for stream_type, expected_codec in expected_codecs.items():
                            if not isinstance(stream_type, str) or not isinstance(expected_codec, str):
                                continue
                            actual_codecs = [
                                stream.codec_name for stream in media.streams if stream.codec_type == stream_type
                            ]
                            contract_errors.extend(
                                f"expected {expected_codec} {stream_type}, found {actual_codec or 'unknown'}"
                                for actual_codec in actual_codecs
                                if actual_codec != expected_codec
                            )
                    expected_pixel_formats = contract.get("pixel_formats")
                    if isinstance(expected_pixel_formats, dict):
                        for stream_type, expected_format in expected_pixel_formats.items():
                            if not isinstance(stream_type, str) or not isinstance(expected_format, str):
                                continue
                            actual_formats = [
                                stream.details.get("pix_fmt")
                                for stream in media.streams
                                if stream.codec_type == stream_type
                            ]
                            contract_errors.extend(
                                f"expected {expected_format} pixel format for {stream_type}, found "
                                f"{actual_format or 'unknown'}"
                                for actual_format in actual_formats
                                if actual_format != expected_format
                            )
                    expected_stream_languages = contract.get("stream_languages")
                    if isinstance(expected_stream_languages, dict):
                        for stream_type, expected_language in expected_stream_languages.items():
                            if not isinstance(stream_type, str) or not isinstance(expected_language, str):
                                continue
                            actual_languages = [
                                stream.language for stream in media.streams if stream.codec_type == stream_type
                            ]
                            contract_errors.extend(
                                f"expected {expected_language} {stream_type} language, found "
                                f"{actual_language or 'unknown'}"
                                for actual_language in actual_languages
                                if actual_language != expected_language
                            )
                required_stream_types = {
                    stream_type
                    for required in (
                        plan.metadata.get("required_stream_types"),
                        contract.get("required_stream_types") if isinstance(contract, dict) else None,
                    )
                    if isinstance(required, list)
                    for stream_type in required
                    if isinstance(stream_type, str)
                }
                actual_types = {stream.codec_type for stream in media.streams}
                contract_errors.extend(
                    f"expected output stream type '{stream_type}', found none"
                    for stream_type in sorted(required_stream_types)
                    if stream_type not in actual_types
                )
                if contract_errors:
                    verification["status"] = "failed"
                    verification["reason"] = "; ".join(contract_errors)
                    errors.extend(f"Output verification failed for {path}: {error}" for error in contract_errors)
                output["verification"] = verification
        outputs.append(output)

    if errors:
        diagnostic = "\n".join(errors)
        if result.stderr:
            diagnostic = f"{diagnostic}\n{result.stderr}"
        return replace(
            result,
            status=JobStatus.FAILED,
            exit_category="validation",
            stderr=diagnostic,
            warnings=tuple(warnings),
            outputs=tuple(outputs),
        )
    return replace(result, warnings=tuple(warnings), outputs=tuple(outputs))


class WorkflowEngine:
    """Compile, preflight, and execute every supported workflow through one public layer."""

    def __init__(self, *, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        self.planner = WorkflowPlanner(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)
        self._preflight = PreflightEngine(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)
        self._output_probe = FFprobeRunner(ffprobe_path)

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
            result = _verify_outputs(execution_plan, result, self._output_probe)
            item = WorkflowExecution(
                input=execution_plan.inputs[0] if execution_plan.inputs else None,
                output=execution_plan.outputs[0] if execution_plan.outputs else None,
                preflight=prepared.preflight,
                result=result,
                plan_metadata=execution_plan.metadata,
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
            result = _verify_outputs(item_plan, result, self._output_probe)
            items.append(
                WorkflowExecution(
                    input=item_plan.inputs[0],
                    output=item_plan.outputs[0],
                    preflight=preflight,
                    result=result,
                    plan_metadata=item_plan.metadata,
                )
            )
        return WorkflowBatch(prepared=prepared, items=tuple(items))
