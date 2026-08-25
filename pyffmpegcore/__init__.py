"""
PyFFmpegCore - The safe, explainable FFmpeg task runner for the terminal, Python, and CI

This package provides tested task workflows, environment diagnostics,
metadata extraction, and progress tracking around local FFmpeg binaries.

Copyright (c) 2025 Othmane BLIAL
"""

from .domain import (
    CapturePolicy,
    CompressOptions,
    ConvertOptions,
    ExecutionPlan,
    ExecutionPolicy,
    JobResult,
    JobStatus,
    MediaInfo,
    OverwritePolicy,
    ProgressEvent,
    ResizeOptions,
    StreamInfo,
    TemporaryFilePolicy,
)
from .errors import (
    CapabilityUnavailableError,
    EnvironmentUnavailableError,
    JobCancelledError,
    JobExecutionError,
    JobTimeoutError,
    PyFFmpegCoreError,
    ValidationError,
)
from .probe import FFprobeRunner
from .profiles import Profile, ProfileRegistry
from .progress import ProgressCallback, ProgressTracker
from .runner import FFmpegRunner

__version__ = "0.2.0"
__all__ = [
    "CapabilityUnavailableError",
    "CapturePolicy",
    "CompressOptions",
    "ConvertOptions",
    "EnvironmentUnavailableError",
    "ExecutionPlan",
    "ExecutionPolicy",
    "FFmpegRunner",
    "FFprobeRunner",
    "JobCancelledError",
    "JobExecutionError",
    "JobResult",
    "JobStatus",
    "JobTimeoutError",
    "MediaInfo",
    "OverwritePolicy",
    "Profile",
    "ProfileRegistry",
    "ProgressCallback",
    "ProgressEvent",
    "ProgressTracker",
    "PyFFmpegCoreError",
    "ResizeOptions",
    "StreamInfo",
    "TemporaryFilePolicy",
    "ValidationError",
]
