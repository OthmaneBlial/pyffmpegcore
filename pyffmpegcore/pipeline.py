"""Strict declarative pipelines composed from typed PyFFmpegCore workflows."""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .domain import ExecutionPlan
from .errors import ValidationError
from .receipt import _validate_state_destination as _validate_state_destination
from .receipt import redact_receipt_value
from .workflow import WorkflowEngine as WorkflowEngine
from .workflow import WorkflowExecution

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


# Keep the original module paths stable while implementation lives in focused modules.
from .pipeline_compiler import (  # noqa: E402, F401
    PipelineCompiler,
    PipelinePreflightEngine,
    PreparedPipeline,
    PreparedPipelineStep,
)
from .pipeline_runner import (  # noqa: E402, F401
    PipelineRunner,
    _cache_key,
    _file_fingerprint,
    _load_pipeline_state,
    _write_pipeline_state,
)
