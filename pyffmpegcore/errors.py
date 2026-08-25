"""Categorized public exceptions for planning and executing media jobs."""

from __future__ import annotations


class PyFFmpegCoreError(RuntimeError):
    """Base error carrying a stable machine-readable category."""

    category = "internal"

    def __init__(self, message: str, *, hint: str | None = None):
        super().__init__(message)
        self.hint = hint


class ValidationError(PyFFmpegCoreError, ValueError):
    """User input or policy is invalid before execution starts."""

    category = "validation"


class EnvironmentUnavailableError(PyFFmpegCoreError):
    """A required executable or host resource is unavailable."""

    category = "environment"


class CapabilityUnavailableError(PyFFmpegCoreError):
    """The installed FFmpeg build cannot satisfy the requested workflow."""

    category = "capability"


class JobExecutionError(PyFFmpegCoreError):
    """FFmpeg or FFprobe started but the media job failed."""

    category = "runtime"


class JobTimeoutError(PyFFmpegCoreError):
    """A job exceeded its explicit timeout."""

    category = "timeout"


class JobCancelledError(PyFFmpegCoreError):
    """A caller explicitly cancelled a running job."""

    category = "cancelled"
