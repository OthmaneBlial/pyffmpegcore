"""
PyFFmpegCore - The safe, explainable FFmpeg task runner for the terminal, Python, and CI

This package provides tested task workflows, environment diagnostics,
metadata extraction, and progress tracking around local FFmpeg binaries.

Copyright (c) 2025 Othmane BLIAL
"""

__version__ = "0.2.0"

from .capabilities import CapabilityInventory
from .domain import (
    CapturePolicy,
    CompressOptions,
    ConvertOptions,
    ExecutionPlan,
    ExecutionPolicy,
    ExecutionStep,
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
from .planning import WorkflowPlanner, parse_size
from .preflight import PreflightCheck, PreflightEngine, PreflightReport
from .probe import FFprobeRunner
from .profiles import Profile, ProfileRegistry
from .progress import ProgressCallback, ProgressTracker
from .receipt import ReceiptBuilder, RunReceipt, build_bug_report, migrate_receipt, validate_receipt
from .runner import FFmpegRunner
from .workflow import PreparedWorkflow, WorkflowBatch, WorkflowEngine, WorkflowExecution

__all__ = [
    "CapabilityUnavailableError",
    "CapabilityInventory",
    "CapturePolicy",
    "CompressOptions",
    "ConvertOptions",
    "EnvironmentUnavailableError",
    "ExecutionPlan",
    "ExecutionPolicy",
    "ExecutionStep",
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
    "PreparedWorkflow",
    "PreflightCheck",
    "PreflightEngine",
    "PreflightReport",
    "ProgressCallback",
    "ProgressEvent",
    "ProgressTracker",
    "PyFFmpegCoreError",
    "ReceiptBuilder",
    "ResizeOptions",
    "RunReceipt",
    "StreamInfo",
    "TemporaryFilePolicy",
    "ValidationError",
    "WorkflowPlanner",
    "WorkflowBatch",
    "WorkflowEngine",
    "WorkflowExecution",
    "build_bug_report",
    "migrate_receipt",
    "parse_size",
    "validate_receipt",
]
