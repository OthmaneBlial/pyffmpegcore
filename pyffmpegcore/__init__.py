"""
PyFFmpegCore - The safe, explainable FFmpeg task runner for the terminal, Python, and CI

This package provides tested task workflows, environment diagnostics,
metadata extraction, and progress tracking around local FFmpeg binaries.

Copyright (c) 2025 Othmane BLIAL
"""

from .probe import FFprobeRunner
from .progress import ProgressCallback, ProgressTracker
from .runner import FFmpegRunner

__version__ = "0.2.0"
__all__ = ["FFmpegRunner", "FFprobeRunner", "ProgressTracker", "ProgressCallback"]
