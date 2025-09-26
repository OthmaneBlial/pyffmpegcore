"""
PyFFmpegCore - A lightweight Python wrapper around FFmpeg/FFprobe

This package provides simple APIs for common video/audio processing tasks
like conversion, compression, metadata extraction, and progress tracking.

Copyright (c) 2025 Othmane BLIAL
"""

from .runner import FFmpegRunner
from .probe import FFprobeRunner
from .progress import ProgressTracker, ProgressCallback

__version__ = "0.1.2"
__all__ = ["FFmpegRunner", "FFprobeRunner", "ProgressTracker", "ProgressCallback"]