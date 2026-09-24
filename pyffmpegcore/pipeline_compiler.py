"""Pipeline compilation and whole-DAG preflight."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .domain import CompressOptions, ConvertOptions, ExecutionPlan, resolve_manifest_path
from .errors import ValidationError
from .pipeline import (
    _STEP_REFERENCE,
    _VARIABLE_REFERENCE,
    PIPELINE_SCHEMA_VERSION,
    PipelineCachePolicy,
    PipelinePlan,
    PipelineSpec,
    PipelineStepPlan,
    PipelineStepSpec,
    _mask_secrets,
)
from .planning import WorkflowPlanner, parse_size
from .preflight import PreflightCheck, PreflightReport
from .profiles import ProfileRegistry
from .workflow import WorkflowEngine


def _substitute_variables(value: Any, variables: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _substitute_variables(child, variables) for key, child in value.items()}
    if isinstance(value, list):
        return [_substitute_variables(child, variables) for child in value]
    if not isinstance(value, str):
        return value

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in variables:
            raise ValidationError(f"missing pipeline variable: {name}")
        return variables[name]

    return _VARIABLE_REFERENCE.sub(replace, value)


def _topological_order(steps: tuple[PipelineStepSpec, ...]) -> tuple[PipelineStepSpec, ...]:
    by_id: dict[str, PipelineStepSpec] = {}
    inferred: dict[str, tuple[str, ...]] = {}
    for step in steps:
        if step.id in by_id:
            raise ValidationError(f"duplicate pipeline step id: {step.id}")
        by_id[step.id] = step
        references = []
        for value in (step.input, step.subtitle):
            match = _STEP_REFERENCE.fullmatch(value or "")
            if match:
                references.append(match.group(1))
        inferred[step.id] = tuple(dict.fromkeys((*step.needs, *references)))
    for step_id, needs in inferred.items():
        for dependency in needs:
            if dependency not in by_id:
                raise ValidationError(f"pipeline step {step_id} requires unknown step: {dependency}")
            if dependency == step_id:
                raise ValidationError(f"pipeline step {step_id} cannot depend on itself")
    ordered: list[PipelineStepSpec] = []
    pending = dict(by_id)
    while pending:
        ready = sorted(
            step_id for step_id in pending if all(dep in {item.id for item in ordered} for dep in inferred[step_id])
        )
        if not ready:
            raise ValidationError("pipeline dependency graph contains a cycle")
        for step_id in ready:
            step = pending.pop(step_id)
            ordered.append(
                PipelineStepSpec(
                    id=step.id,
                    input=step.input,
                    output=step.output,
                    needs=inferred[step.id],
                    profile=step.profile,
                    workflow=step.workflow,
                    subtitle=step.subtitle,
                    options=step.options,
                    force=step.force,
                )
            )
    return tuple(ordered)


def _strict_options(options: dict[str, Any], allowed: set[str], workflow: str) -> dict[str, Any]:
    unknown = sorted(set(options) - allowed)
    if unknown:
        raise ValidationError(f"unknown {workflow} options: {', '.join(unknown)}")
    return options


def _compile_workflow(
    step: PipelineStepSpec,
    planner: WorkflowPlanner,
    input_value: str,
    output_value: str,
    subtitle_value: str | None,
    *,
    force: bool,
    timeout_seconds: float | None,
) -> ExecutionPlan:
    options = deepcopy(step.options)
    if step.profile is not None:
        if options:
            raise ValidationError(f"profile step {step.id} cannot override versioned profile options")
        return ProfileRegistry().plan(
            step.profile,
            planner,
            input_value,
            output_value,
            subtitle_file=subtitle_value,
            force=force,
            timeout_seconds=timeout_seconds,
        )
    workflow = step.workflow or ""
    try:
        if workflow == "convert":
            _strict_options(options, set(ConvertOptions.__dataclass_fields__), workflow)
            return planner.convert(
                input_value,
                output_value,
                ConvertOptions(**options),
                force=force,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "compress":
            _strict_options(options, set(CompressOptions.__dataclass_fields__), workflow)
            if isinstance(options.get("target_size_bytes"), str):
                options["target_size_bytes"] = parse_size(options["target_size_bytes"])
            return planner.compress(
                input_value,
                output_value,
                CompressOptions(**options),
                force=force,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "extract-audio":
            _strict_options(options, {"audio_codec", "audio_bitrate", "sample_rate", "channels", "threads"}, workflow)
            return planner.extract_audio(
                input_value,
                output_value,
                **options,
                force=force,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "thumbnail":
            _strict_options(options, {"timestamp", "width", "height", "quality"}, workflow)
            return planner.thumbnail(
                input_value,
                output_value,
                **options,
                force=force,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "waveform":
            _strict_options(options, {"width", "height", "colors"}, workflow)
            return planner.waveform(
                input_value,
                output_value,
                **options,
                force=force,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "normalize-audio":
            _strict_options(options, {"method", "target_i", "target_tp", "target_lra"}, workflow)
            return planner.normalize_audio(
                input_value,
                output_value,
                **options,
                force=force,
                timeout_seconds=timeout_seconds,
            )
        if workflow in {"subtitles/add", "subtitles/burn"}:
            _strict_options(options, {"language", "font_size", "font_color"}, workflow)
            return planner.subtitles(
                workflow.split("/", 1)[1],
                input_value,
                output_value,
                subtitle_file=subtitle_value,
                **options,
                force=force,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "image/convert":
            _strict_options(options, {"quality", "resize"}, workflow)
            resize = options.get("resize")
            if isinstance(resize, list):
                options["resize"] = tuple(resize)
            return planner.image(
                input_value,
                output_value,
                **options,
                force=force,
                timeout_seconds=timeout_seconds,
            )
    except TypeError as exc:
        raise ValidationError(f"invalid typed options for pipeline step {step.id}: {exc}") from exc
    raise ValidationError(f"unsupported typed pipeline workflow: {workflow}")


class PipelineCompiler:
    """Resolve variables/dependencies and compile every step through the typed planner."""

    def __init__(self, *, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        self.planner = WorkflowPlanner(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)

    def compile(
        self,
        spec: PipelineSpec,
        *,
        variables: dict[str, str] | None = None,
        force: bool = False,
        timeout_seconds: float | None = None,
        cache_enabled: bool | None = None,
    ) -> PipelinePlan:
        """Resolve pipeline variables and compile steps without running FFmpeg.

        Dependency references become producer output paths. Secret values are
        retained only for redaction in the resulting plan and receipts.
        """
        selected_variables = {**spec.variables, **(variables or {})}
        missing_secrets = sorted(set(spec.secret_variables) - set(selected_variables))
        if missing_secrets:
            raise ValidationError(f"missing secret pipeline variables: {', '.join(missing_secrets)}")
        unknown_variables = sorted(set(selected_variables) - (set(spec.variables) | set(spec.secret_variables)))
        if unknown_variables:
            raise ValidationError(f"unknown pipeline variable overrides: {', '.join(unknown_variables)}")
        ordered = _topological_order(spec.steps)
        outputs: dict[str, str] = {}
        plans = []
        output_keys: dict[str, str] = {}
        for step in ordered:
            raw_input = _substitute_variables(step.input, selected_variables)
            raw_output = _substitute_variables(step.output, selected_variables)
            raw_subtitle = _substitute_variables(step.subtitle, selected_variables) if step.subtitle else None
            reference = _STEP_REFERENCE.fullmatch(raw_input)
            input_value = outputs[reference.group(1)] if reference else resolve_manifest_path(raw_input, spec.base_dir)
            subtitle_reference = _STEP_REFERENCE.fullmatch(raw_subtitle or "")
            subtitle_value = (
                outputs[subtitle_reference.group(1)]
                if subtitle_reference
                else resolve_manifest_path(raw_subtitle, spec.base_dir)
                if raw_subtitle
                else None
            )
            output_value = resolve_manifest_path(raw_output, spec.base_dir)
            collision_key = output_value.casefold()
            if collision_key in output_keys:
                raise ValidationError(
                    f"pipeline output collision between {output_keys[collision_key]} and {step.id}: {output_value}"
                )
            output_keys[collision_key] = step.id
            options = _substitute_variables(step.options, selected_variables)
            compiled_step = PipelineStepSpec(
                id=step.id,
                input=input_value,
                output=output_value,
                needs=step.needs,
                profile=step.profile,
                workflow=step.workflow,
                subtitle=subtitle_value,
                options=options,
                force=step.force,
            )
            plan = _compile_workflow(
                compiled_step,
                self.planner,
                input_value,
                output_value,
                subtitle_value,
                force=force or step.force,
                timeout_seconds=timeout_seconds,
            )
            outputs[step.id] = output_value
            plans.append(PipelineStepPlan(step.id, step.needs, plan))
        cache = PipelineCachePolicy(
            enabled=spec.cache.enabled if cache_enabled is None else cache_enabled,
            directory=resolve_manifest_path(spec.cache.directory, spec.base_dir),
            content_aware=spec.cache.content_aware,
        )
        return PipelinePlan(
            name=spec.name,
            description=spec.description,
            steps=tuple(plans),
            cache=cache,
            base_dir=spec.base_dir,
            secret_values=tuple(selected_variables[name] for name in spec.secret_variables),
        )


@dataclass(frozen=True, slots=True)
class PreparedPipelineStep:
    id: str
    needs: tuple[str, ...]
    plan: ExecutionPlan
    preflight: PreflightReport


@dataclass(frozen=True, slots=True)
class PreparedPipeline:
    """Whole-pipeline structural, capability, and external-input preflight facts."""

    pipeline: PipelinePlan
    steps: tuple[PreparedPipelineStep, ...]

    @property
    def ok(self) -> bool:
        return all(step.preflight.ok for step in self.steps)

    def to_dict(self) -> dict[str, object]:
        """Return per-step preflight facts and the aggregate pipeline status."""
        return _mask_secrets(
            {
                "schema_version": PIPELINE_SCHEMA_VERSION,
                "pipeline": self.pipeline.to_dict(),
                "ok": self.ok,
                "steps": [
                    {"id": step.id, "needs": list(step.needs), "preflight": step.preflight.to_dict()}
                    for step in self.steps
                ],
            },
            self.pipeline.secret_values,
        )


class PipelinePreflightEngine:
    """Preflight an entire DAG while explicitly deferring dependency outputs."""

    def __init__(self, *, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        self.engine = WorkflowEngine(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)

    def prepare(self, pipeline: PipelinePlan, *, allow_existing_outputs: bool = False) -> PreparedPipeline:
        """Preflight each step and defer missing inputs produced by dependencies.

        Existing outputs remain errors unless explicitly allowed for a later
        cache or resume check; this method never executes a step.
        """
        outputs = {step.id: set(step.plan.outputs) for step in pipeline.steps}
        prepared = []
        for step in pipeline.steps:
            report = self.engine.prepare(step.plan).preflight
            dependency_outputs = set().union(*(outputs[need] for need in step.needs)) if step.needs else set()
            checks = []
            for check in report.checks:
                deferred = any(check.name in {f"input/{value}", f"probe/{value}"} for value in dependency_outputs)
                if deferred and check.status == "fail":
                    checks.append(
                        PreflightCheck(
                            check.name,
                            "warn",
                            "Deferred until the declared dependency produces this input",
                        )
                    )
                elif allow_existing_outputs and check.name.startswith("collision/") and check.status == "fail":
                    checks.append(
                        PreflightCheck(
                            check.name,
                            "warn",
                            "Existing output will be reused only if its saved cache/resume key matches",
                        )
                    )
                else:
                    checks.append(check)
            prepared.append(
                PreparedPipelineStep(step.id, step.needs, step.plan, PreflightReport(report.workflow, tuple(checks)))
            )
        return PreparedPipeline(pipeline, tuple(prepared))
