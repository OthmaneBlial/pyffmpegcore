"""Stable public domain types used by the CLI, Python API, and receipts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .errors import ValidationError

PLAN_SCHEMA_VERSION = "1.0"
RESULT_SCHEMA_VERSION = "1.0"


class StringEnum(str, Enum):
    """Python 3.10-compatible string enumeration."""

    def __str__(self) -> str:
        return self.value


class OverwritePolicy(StringEnum):
    REFUSE = "refuse"
    REPLACE = "replace"


class CapturePolicy(StringEnum):
    FULL = "full"
    TAIL = "tail"
    DISCARD = "discard"


class TemporaryFilePolicy(StringEnum):
    CLEAN = "clean"
    KEEP_ON_ERROR = "keep-on-error"
    KEEP = "keep"


class JobStatus(StringEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed-out"


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    """Explicit process, overwrite, capture, and cleanup behavior."""

    overwrite: OverwritePolicy = OverwritePolicy.REFUSE
    timeout_seconds: float | None = None
    stdout: CapturePolicy = CapturePolicy.TAIL
    stderr: CapturePolicy = CapturePolicy.TAIL
    capture_tail_chars: int = 16_384
    temporary_files: TemporaryFilePolicy = TemporaryFilePolicy.CLEAN

    def __post_init__(self) -> None:
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValidationError("timeout_seconds must be positive when provided")
        if self.capture_tail_chars <= 0:
            raise ValidationError("capture_tail_chars must be positive")


@dataclass(frozen=True, slots=True)
class StreamInfo:
    """Typed stream facts while preserving metadata needed for safe decisions."""

    index: int
    codec_type: str
    codec_name: str | None = None
    profile: str | None = None
    width: int | None = None
    height: int | None = None
    sample_rate: int | None = None
    channels: int | None = None
    bit_rate: int | None = None
    duration: float | None = None
    language: str | None = None
    rotation: float | None = None
    tags: dict[str, str] = field(default_factory=dict)
    disposition: dict[str, int] = field(default_factory=dict)
    color: dict[str, str] = field(default_factory=dict)
    side_data: tuple[dict[str, Any], ...] = ()
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MediaInfo:
    """Typed container, stream, and chapter information from FFprobe."""

    path: str
    format_name: str | None = None
    format_long_name: str | None = None
    duration: float | None = None
    size: int | None = None
    bit_rate: int | None = None
    tags: dict[str, str] = field(default_factory=dict)
    streams: tuple[StreamInfo, ...] = ()
    chapters: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    """Versioned progress fact suitable for callbacks or JSON Lines output."""

    schema_version: str = "1.0"
    sequence: int = 0
    status: str = "running"
    frame: int | None = None
    time_seconds: float | None = None
    speed: float | None = None
    item: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ExecutionStep:
    """One named argument-vector step inside a multi-pass plan."""

    name: str
    command: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.command or not self.command[0]:
            raise ValidationError("execution step requires a name and executable command")


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Deterministic, non-shell execution plan for one media workflow."""

    workflow: str
    command: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    policy: ExecutionPolicy = field(default_factory=ExecutionPolicy)
    required_capabilities: tuple[str, ...] = ()
    selected_streams: tuple[str, ...] = ()
    operations: tuple[str, ...] = ()
    steps: tuple[ExecutionStep, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.workflow.strip():
            raise ValidationError("workflow must not be empty")
        if not self.command or not self.command[0]:
            raise ValidationError("command must contain an executable")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["policy"]["overwrite"] = self.policy.overwrite.value
        data["policy"]["stdout"] = self.policy.stdout.value
        data["policy"]["stderr"] = self.policy.stderr.value
        data["policy"]["temporary_files"] = self.policy.temporary_files.value
        return data

    @property
    def execution_steps(self) -> tuple[ExecutionStep, ...]:
        """Return explicit steps or a single implicit primary step."""
        return self.steps or (ExecutionStep(name=self.workflow, command=self.command),)


@dataclass(frozen=True, slots=True)
class JobResult:
    """Stable execution result with diagnostics and output evidence."""

    workflow: str
    command: tuple[str, ...]
    status: JobStatus
    exit_category: str
    returncode: int | None
    elapsed_seconds: float
    stdout: str | None = None
    stderr: str | None = None
    progress: ProgressEvent | None = None
    warnings: tuple[str, ...] = ()
    outputs: tuple[dict[str, Any], ...] = ()
    schema_version: str = RESULT_SCHEMA_VERSION

    @property
    def succeeded(self) -> bool:
        return self.status is JobStatus.SUCCEEDED

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True, slots=True)
class ConvertOptions:
    video_codec: str | None = None
    audio_codec: str | None = None
    video_bitrate: str | None = None
    audio_bitrate: str | None = None
    pixel_format: str = "yuv420p"
    threads: int | None = None
    audio_only: bool = False
    hardware_acceleration: str | None = None
    preserve_all_streams: bool = False

    def __post_init__(self) -> None:
        if self.threads is not None and self.threads <= 0:
            raise ValidationError("threads must be positive when provided")
        if self.preserve_all_streams and any(
            (
                self.video_codec,
                self.audio_codec,
                self.video_bitrate,
                self.audio_bitrate,
                self.threads,
                self.audio_only,
                self.hardware_acceleration,
            )
        ):
            raise ValidationError(
                "preserve_all_streams cannot be combined with audio-only, codec, "
                "bitrate, threads, or hardware-acceleration options"
            )


@dataclass(frozen=True, slots=True)
class ResizeOptions:
    width: int
    height: int
    video_codec: str | None = None
    audio_codec: str | None = None
    pixel_format: str = "yuv420p"
    threads: int | None = None

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValidationError("width and height must be positive integers")
        if self.threads is not None and self.threads <= 0:
            raise ValidationError("threads must be positive when provided")


@dataclass(frozen=True, slots=True)
class CompressOptions:
    target_size_bytes: int | None = None
    crf: int = 23
    two_pass: bool = True
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate: str | None = None
    audio_bitrate: str = "128k"
    preset: str = "medium"
    pixel_format: str = "yuv420p"
    threads: int | None = None
    container_overhead_percent: float = 5.0
    minimum_video_bitrate: int = 100 * 1024

    def __post_init__(self) -> None:
        if self.target_size_bytes is not None and self.target_size_bytes <= 0:
            raise ValidationError("target_size_bytes must be positive when provided")
        if not 0 <= self.crf <= 51:
            raise ValidationError("crf must be between 0 and 51")
        if self.threads is not None and self.threads <= 0:
            raise ValidationError("threads must be positive when provided")
        if not 0 <= self.container_overhead_percent < 100:
            raise ValidationError("container_overhead_percent must be between 0 and 100")
        if self.minimum_video_bitrate <= 0:
            raise ValidationError("minimum_video_bitrate must be positive")


def normalized_path(path: str | Path) -> str:
    """Return an absolute path without requiring it to exist."""
    return str(Path(path).expanduser().resolve())
