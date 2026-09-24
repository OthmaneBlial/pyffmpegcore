"""Strict declarative pipelines composed from typed PyFFmpegCore workflows."""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .domain import CompressOptions, ConvertOptions, ExecutionPlan, resolve_manifest_path
from .errors import ValidationError
from .planning import WorkflowPlanner, parse_size
from .preflight import PreflightCheck, PreflightReport
from .profiles import ProfileRegistry
from .receipt import _validate_state_destination as _validate_state_destination
from .receipt import redact_receipt_value
from .workflow import WorkflowEngine, WorkflowExecution

PIPELINE_SCHEMA_VERSION = "1.0"
PIPELINE_STATE_SCHEMA_VERSION = "1.0"
_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,79}$")
_VARIABLE_REFERENCE = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
_STEP_REFERENCE = re.compile(r"^\$\{steps\.([A-Za-z][A-Za-z0-9_-]{0,79})\.output\}$")
_SECRET_NAME = re.compile(r"(?i)(authorization|api[-_]?key|password|secret|token)")
_ROOT_FIELDS = {"schema_version", "name", "description", "variables", "secret_variables", "cache", "steps"}
_STEP_FIELDS = {"id", "needs", "profile", "workflow", "input", "output", "subtitle", "options", "force"}
_CACHE_FIELDS = {"enabled", "directory", "content_aware"}
_WORKFLOWS = {
    "convert",
    "compress",
    "extract-audio",
    "thumbnail",
    "waveform",
    "normalize-audio",
    "subtitles/add",
    "subtitles/burn",
    "image/convert",
}


def _load_document(path: Path) -> dict[str, Any]:
    try:
        if path.suffix.casefold() == ".json":
            document = json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix.casefold() == ".toml":
            try:
                import tomllib
            except ModuleNotFoundError:  # pragma: no cover - Python 3.10
                import tomli as tomllib

            with path.open("rb") as handle:
                document = tomllib.load(handle)
        else:
            raise ValidationError("pipeline files must use .json or .toml")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ValidationError(f"unable to read pipeline: {exc}") from exc
    if not isinstance(document, dict):
        raise ValidationError("pipeline document must be an object/table")
    return document


def _mask_secrets(value: Any, secrets: tuple[str, ...]) -> Any:
    redacted = redact_receipt_value(value)
    if isinstance(redacted, dict):
        return {key: _mask_secrets(child, secrets) for key, child in redacted.items()}
    if isinstance(redacted, list):
        return [_mask_secrets(child, secrets) for child in redacted]
    if isinstance(redacted, str):
        for secret in sorted((item for item in secrets if item), key=len, reverse=True):
            redacted = redacted.replace(secret, "<redacted>")
    return redacted


@dataclass(frozen=True, slots=True)
class PipelineCachePolicy:
    """Optional output-validity cache; content hashing is explicit."""

    enabled: bool = False
    directory: str = ".pyffmpegcore/cache"
    content_aware: bool = False

    def __post_init__(self) -> None:
        if not self.directory.strip():
            raise ValidationError("pipeline cache directory must not be empty")

    def to_dict(self) -> dict[str, object]:
        """Return JSON-compatible cache settings."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PipelineStepSpec:
    """One strict declarative step before variable and dependency resolution."""

    id: str
    input: str
    output: str
    needs: tuple[str, ...] = ()
    profile: str | None = None
    workflow: str | None = None
    subtitle: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
    force: bool = False

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.id):
            raise ValidationError(f"invalid pipeline step id: {self.id!r}")
        if (self.profile is None) == (self.workflow is None):
            raise ValidationError(f"pipeline step {self.id} requires exactly one of profile or workflow")
        if self.workflow is not None and self.workflow not in _WORKFLOWS:
            raise ValidationError(f"unsupported typed pipeline workflow: {self.workflow}")
        if not self.input or not self.output:
            raise ValidationError(f"pipeline step {self.id} requires input and output")
        if len(set(self.needs)) != len(self.needs):
            raise ValidationError(f"pipeline step {self.id} contains duplicate dependencies")

    def to_dict(self) -> dict[str, object]:
        """Serialize the declarative step with JSON-compatible options."""
        result: dict[str, object] = {
            "id": self.id,
            "input": self.input,
            "output": self.output,
            "needs": list(self.needs),
            "options": deepcopy(self.options),
            "force": self.force,
        }
        if self.profile is not None:
            result["profile"] = self.profile
        if self.workflow is not None:
            result["workflow"] = self.workflow
        if self.subtitle is not None:
            result["subtitle"] = self.subtitle
        return result


@dataclass(frozen=True, slots=True)
class PipelineSpec:
    """Versioned pipeline source with strict variables, cache, and typed steps."""

    name: str
    steps: tuple[PipelineStepSpec, ...]
    description: str = ""
    variables: dict[str, str] = field(default_factory=dict)
    secret_variables: tuple[str, ...] = ()
    cache: PipelineCachePolicy = field(default_factory=PipelineCachePolicy)
    base_dir: Path = field(default_factory=lambda: Path.cwd())
    schema_version: str = PIPELINE_SCHEMA_VERSION

    @classmethod
    def read(cls, path: str | Path) -> PipelineSpec:
        selected = Path(path).resolve()
        return cls.from_dict(_load_document(selected), base_dir=selected.parent)

    @classmethod
    def from_dict(cls, document: Any, *, base_dir: str | Path = ".") -> PipelineSpec:
        if not isinstance(document, dict):
            raise ValidationError("pipeline must be an object/table")
        unknown = sorted(set(document) - _ROOT_FIELDS)
        if unknown:
            raise ValidationError(f"unknown pipeline fields: {', '.join(unknown)}")
        if document.get("schema_version") != PIPELINE_SCHEMA_VERSION:
            raise ValidationError(f"pipeline schema_version must be {PIPELINE_SCHEMA_VERSION!r}")
        name = document.get("name")
        if not isinstance(name, str) or not _IDENTIFIER.fullmatch(name):
            raise ValidationError("pipeline name must be a stable identifier")
        description = document.get("description", "")
        if not isinstance(description, str):
            raise ValidationError("pipeline description must be a string")
        variables = document.get("variables", {})
        if not isinstance(variables, dict) or not all(
            isinstance(key, str) and _IDENTIFIER.fullmatch(key) and isinstance(value, str)
            for key, value in variables.items()
        ):
            raise ValidationError("pipeline variables must map stable names to string defaults")
        secret_variables = document.get("secret_variables", [])
        if not isinstance(secret_variables, list) or not all(
            isinstance(value, str) and _IDENTIFIER.fullmatch(value) for value in secret_variables
        ):
            raise ValidationError("pipeline secret_variables must be an array of stable names")
        if set(secret_variables) & set(variables):
            raise ValidationError("secret variables must not have values inside the pipeline file")
        for key, value in variables.items():
            if _SECRET_NAME.search(key) or _SECRET_NAME.search(value):
                raise ValidationError(f"pipeline variable {key} looks secret; declare it in secret_variables")

        cache_payload = document.get("cache", {})
        if not isinstance(cache_payload, dict):
            raise ValidationError("pipeline cache must be an object/table")
        unknown_cache = sorted(set(cache_payload) - _CACHE_FIELDS)
        if unknown_cache:
            raise ValidationError(f"unknown pipeline cache fields: {', '.join(unknown_cache)}")
        if any(
            not isinstance(cache_payload.get(key), bool) for key in ("enabled", "content_aware") if key in cache_payload
        ):
            raise ValidationError("pipeline cache enabled and content_aware must be booleans")
        directory = cache_payload.get("directory", ".pyffmpegcore/cache")
        if not isinstance(directory, str):
            raise ValidationError("pipeline cache directory must be a string")
        cache = PipelineCachePolicy(
            enabled=cache_payload.get("enabled", False),
            directory=directory,
            content_aware=cache_payload.get("content_aware", False),
        )

        steps_payload = document.get("steps")
        if not isinstance(steps_payload, list) or not steps_payload:
            raise ValidationError("pipeline steps must be a non-empty array")
        steps = []
        for payload in steps_payload:
            if not isinstance(payload, dict):
                raise ValidationError("each pipeline step must be an object/table")
            unknown_step = sorted(set(payload) - _STEP_FIELDS)
            if unknown_step:
                raise ValidationError(f"unknown pipeline step fields: {', '.join(unknown_step)}")
            needs = payload.get("needs", [])
            options = payload.get("options", {})
            if not isinstance(needs, list) or not all(isinstance(value, str) for value in needs):
                raise ValidationError("pipeline step needs must be an array of ids")
            if not isinstance(options, dict):
                raise ValidationError("pipeline step options must be an object/table")
            if not isinstance(payload.get("force", False), bool):
                raise ValidationError("pipeline step force must be a boolean")
            string_fields = ("id", "input", "output")
            if any(not isinstance(payload.get(key), str) for key in string_fields):
                raise ValidationError("pipeline steps require string id, input, and output fields")
            for optional in ("profile", "workflow", "subtitle"):
                if optional in payload and not isinstance(payload[optional], str):
                    raise ValidationError(f"pipeline step {optional} must be a string")
            steps.append(
                PipelineStepSpec(
                    id=payload["id"],
                    input=payload["input"],
                    output=payload["output"],
                    needs=tuple(needs),
                    profile=payload.get("profile"),
                    workflow=payload.get("workflow"),
                    subtitle=payload.get("subtitle"),
                    options=deepcopy(options),
                    force=payload.get("force", False),
                )
            )
        return cls(
            name=name,
            description=description,
            variables=dict(variables),
            secret_variables=tuple(secret_variables),
            cache=cache,
            steps=tuple(steps),
            base_dir=Path(base_dir).resolve(),
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize the versioned manifest without its local base directory."""
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "description": self.description,
            "variables": dict(sorted(self.variables.items())),
            "secret_variables": list(self.secret_variables),
            "cache": self.cache.to_dict(),
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass(frozen=True, slots=True)
class PipelineStepPlan:
    """One topologically ordered typed plan and its dependencies."""

    id: str
    needs: tuple[str, ...]
    plan: ExecutionPlan


@dataclass(frozen=True, slots=True)
class PipelinePlan:
    """Compiled DAG whose steps contain argument arrays, never shell strings."""

    name: str
    description: str
    steps: tuple[PipelineStepPlan, ...]
    cache: PipelineCachePolicy
    base_dir: Path
    secret_values: tuple[str, ...] = ()
    schema_version: str = PIPELINE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Serialize compiled plans while masking declared secret values."""
        return _mask_secrets(
            {
                "schema_version": self.schema_version,
                "name": self.name,
                "description": self.description,
                "cache": self.cache.to_dict(),
                "steps": [
                    {"id": step.id, "needs": list(step.needs), "plan": step.plan.to_dict()} for step in self.steps
                ],
            },
            self.secret_values,
        )

    def graph(self, format: str = "text") -> str:
        """Render the dependency DAG as text, Mermaid, or Graphviz DOT."""
        if format == "text":
            return "\n".join(
                f"{step.id} <- {', '.join(step.needs) if step.needs else '<source>'}" for step in self.steps
            )
        if format == "mermaid":
            lines = ["flowchart LR"]
            for step in self.steps:
                lines.append(f'  {step.id}["{step.id}: {step.plan.workflow}"]')
                for dependency in step.needs:
                    lines.append(f"  {dependency} --> {step.id}")
            return "\n".join(lines)
        if format == "dot":
            lines = [f'digraph "{self.name}" {{']
            for step in self.steps:
                lines.append(f'  "{step.id}" [label="{step.id}: {step.plan.workflow}"];')
                for dependency in step.needs:
                    lines.append(f'  "{dependency}" -> "{step.id}";')
            lines.append("}")
            return "\n".join(lines)
        raise ValidationError("pipeline graph format must be text, mermaid, or dot")


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


@dataclass(frozen=True, slots=True)
class PipelineEvent:
    sequence: int
    event: str
    step_id: str
    detail: str | None = None
    schema_version: str = PIPELINE_SCHEMA_VERSION

    def to_dict(self, secrets: tuple[str, ...] = ()) -> dict[str, object]:
        """Serialize this event and mask supplied secret values."""
        return _mask_secrets(asdict(self), secrets)


@dataclass(frozen=True, slots=True)
class PipelineStepOutcome:
    step_id: str
    status: str
    cache_key: str
    execution: WorkflowExecution | None = None
    receipt: str | None = None
    detail: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status in {"succeeded", "resumed", "cached"}

    def to_dict(self, secrets: tuple[str, ...] = ()) -> dict[str, object]:
        """Serialize this step outcome and redact nested execution evidence."""
        return _mask_secrets(
            {
                "step_id": self.step_id,
                "status": self.status,
                "cache_key": self.cache_key,
                "execution": self.execution.to_dict() if self.execution else None,
                "receipt": self.receipt,
                "detail": self.detail,
            },
            secrets,
        )


@dataclass(frozen=True, slots=True)
class PipelineRun:
    pipeline: PipelinePlan
    items: tuple[PipelineStepOutcome, ...]
    schema_version: str = PIPELINE_SCHEMA_VERSION

    @property
    def succeeded_count(self) -> int:
        return sum(item.succeeded for item in self.items)

    @property
    def failed_count(self) -> int:
        return sum(item.status == "failed" for item in self.items)

    @property
    def blocked_count(self) -> int:
        return sum(item.status == "blocked" for item in self.items)

    @property
    def cancelled_count(self) -> int:
        return sum(item.status == "cancelled" for item in self.items)

    @property
    def succeeded(self) -> bool:
        return self.succeeded_count == len(self.items)

    def to_dict(self) -> dict[str, object]:
        """Serialize ordered outcomes with a stable summary."""
        return {
            "schema_version": self.schema_version,
            "pipeline": self.pipeline.to_dict(),
            "items": [item.to_dict(self.pipeline.secret_values) for item in self.items],
            "summary": {
                "total": len(self.items),
                "succeeded": self.succeeded_count,
                "failed": self.failed_count,
                "blocked": self.blocked_count,
                "cancelled": self.cancelled_count,
            },
        }


def variables_from_environment(names: list[str]) -> dict[str, str]:
    """Read named pipeline variables from the environment without accepting inline secrets."""
    result = {}
    for name in names:
        if not _IDENTIFIER.fullmatch(name):
            raise ValidationError(f"invalid environment variable name: {name}")
        if name not in os.environ:
            raise ValidationError(f"pipeline environment variable is not set: {name}")
        result[name] = os.environ[name]
    return result


def migrate_pipeline_document(
    document: dict[str, Any], target_version: str = PIPELINE_SCHEMA_VERSION
) -> dict[str, Any]:
    """Validate and canonicalize a pipeline before future schema migrations are added."""
    source = document.get("schema_version") if isinstance(document, dict) else None
    if target_version != PIPELINE_SCHEMA_VERSION:
        raise ValidationError(f"unsupported target pipeline schema: {target_version}")
    if source != PIPELINE_SCHEMA_VERSION:
        raise ValidationError(f"no pipeline migration path from {source!r} to {target_version!r}")
    return PipelineSpec.from_dict(deepcopy(document)).to_dict()


# Keep the original module paths stable while execution lives in its own module.
from .pipeline_runner import (  # noqa: E402, F401
    PipelineRunner,
    _cache_key,
    _file_fingerprint,
    _load_pipeline_state,
    _write_pipeline_state,
)
