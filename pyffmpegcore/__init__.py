"""
PyFFmpegCore - A lightweight Python wrapper around FFmpeg/FFprobe

This package provides simple APIs for common video/audio processing tasks
like conversion, compression, metadata extraction, and progress tracking.

Copyright (c) 2025 Othmane BLIAL
"""

from .probe import FFprobeRunner
from .progress import ProgressCallback, ProgressTracker
from .runner import FFmpegRunner

__version__ = "0.2.0"
__all__ = ["FFmpegRunner", "FFprobeRunner", "ProgressTracker", "ProgressCallback"]
