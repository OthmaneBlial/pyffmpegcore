"""Typed workflow facade plus an explicit low-level FFmpeg escape hatch."""

from __future__ import annotations

import shlex
import subprocess
import threading
from collections.abc import Callable

from .domain import (
    CompressOptions,
    ConvertOptions,
    ExecutionPlan,
    JobResult,
    OverwritePolicy,
    ProgressEvent,
    ResizeOptions,
)
from .executor import ExecutionEngine
from .planning import WorkflowPlanner
from .progress import ProgressTracker


def escape_path_for_filter(path: str) -> str:
    """Escape a file path for use inside an FFmpeg filter expression."""
    escaped = path.replace("\\", "/").replace(":", "\\:")
    return escaped.replace("'", "\\'")


def escape_path_for_concat(path: str) -> str:
    """Quote a path for an FFmpeg concat-demuxer manifest."""
    escaped = path.replace("\\", "/").replace("'", "'\\''")
    return f"'{escaped}'"


class FFmpegRunner:
    """Execute typed workflows or an explicit non-shell argument vector."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    @property
    def planner(self) -> WorkflowPlanner:
        """Return a planner configured with this runner's executable paths."""
        return WorkflowPlanner(ffmpeg_path=self.ffmpeg_path, ffprobe_path=self.ffprobe_path)

    def execute_plan(
        self,
        plan: ExecutionPlan,
        *,
        cancellation: threading.Event | None = None,
        progress_callback: Callable[[ProgressEvent], None] | None = None,
    ) -> JobResult:
        """Execute a typed plan and return a stable structured result."""
        return ExecutionEngine().execute(
            plan,
            cancellation=cancellation,
            progress_callback=progress_callback,
        )

    def run(
        self,
        args: list[str],
        progress_callback: Callable[[dict[str, object]], None] | None = None,
        *,
        overwrite: OverwritePolicy = OverwritePolicy.REFUSE,
    ) -> subprocess.CompletedProcess[str]:
        """Run a raw argument vector without a shell and with explicit overwrite policy."""
        command_args = list(args)
        if "-n" not in command_args and "-y" not in command_args:
            command_args.insert(0, "-y" if overwrite is OverwritePolicy.REPLACE else "-n")
        command = [self.ffmpeg_path, *command_args]
        try:
            result = (
                ProgressTracker(progress_callback).run(command)
                if progress_callback is not None
                else subprocess.run(command, capture_output=True, text=True)
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"FFmpeg executable '{self.ffmpeg_path}' was not found. Install FFmpeg or pass a valid ffmpeg_path."
            ) from exc
        return self._annotate_failure(command, result)

    def run_with_progress(
        self,
        args: list[str],
        show_percentage: bool = True,
        *,
        overwrite: OverwritePolicy = OverwritePolicy.REFUSE,
    ) -> subprocess.CompletedProcess[str]:
        """Run the low-level escape hatch and print its legacy progress stream."""

        def progress_callback(progress: dict[str, object]) -> None:
            if progress.get("status") == "end":
                print("\rProgress: complete", flush=True)
            elif show_percentage and isinstance(progress.get("time_seconds"), float):
                print(f"\rProgress time: {progress['time_seconds']:.2f}s", end="", flush=True)
            elif progress.get("frame") is not None:
                print(f"\rFrame: {progress['frame']}", end="", flush=True)

        return self.run(args, progress_callback, overwrite=overwrite)

    def _run_workflow(
        self,
        plan: ExecutionPlan,
        *,
        progress_callback: Callable[[ProgressEvent], None] | None = None,
    ) -> JobResult:
        from .workflow import WorkflowEngine

        batch = WorkflowEngine(ffmpeg_path=self.ffmpeg_path, ffprobe_path=self.ffprobe_path).run(
            plan,
            progress_callback=progress_callback,
        )
        return batch.items[0].result

    def convert(
        self,
        input_file: str,
        output_file: str,
        *,
        video_codec: str | None = None,
        audio_codec: str | None = None,
        video_bitrate: str | None = None,
        audio_bitrate: str | None = None,
        pixel_format: str = "yuv420p",
        threads: int | None = None,
        audio_only: bool = False,
        hardware_acceleration: str | None = None,
        preserve_all_streams: bool = False,
        force: bool = False,
        progress_callback: Callable[[ProgressEvent], None] | None = None,
    ) -> JobResult:
        """Plan, preflight, and execute a typed conversion."""
        options = ConvertOptions(
            video_codec=video_codec,
            audio_codec=audio_codec,
            video_bitrate=video_bitrate,
            audio_bitrate=audio_bitrate,
            pixel_format=pixel_format,
            threads=threads,
            audio_only=audio_only,
            hardware_acceleration=hardware_acceleration,
            preserve_all_streams=preserve_all_streams,
        )
        return self._run_workflow(
            self.planner.convert(input_file, output_file, options, force=force),
            progress_callback=progress_callback,
        )

    def resize(
        self,
        input_file: str,
        output_file: str,
        width: int,
        height: int,
        *,
        video_codec: str | None = None,
        audio_codec: str | None = None,
        pixel_format: str = "yuv420p",
        threads: int | None = None,
        force: bool = False,
        progress_callback: Callable[[ProgressEvent], None] | None = None,
    ) -> JobResult:
        """Plan, preflight, and execute a typed resize."""
        options = ResizeOptions(
            width=width,
            height=height,
            video_codec=video_codec,
            audio_codec=audio_codec,
            pixel_format=pixel_format,
            threads=threads,
        )
        return self._run_workflow(
            self.planner.resize(input_file, output_file, options, force=force),
            progress_callback=progress_callback,
        )

    def compress(
        self,
        input_file: str,
        output_file: str,
        *,
        target_size_kb: int | None = None,
        crf: int = 23,
        two_pass: bool = True,
        video_codec: str = "libx264",
        audio_codec: str = "aac",
        video_bitrate: str | None = None,
        audio_bitrate: str = "128k",
        preset: str = "medium",
        pixel_format: str = "yuv420p",
        threads: int | None = None,
        container_overhead_percent: float = 5.0,
        minimum_video_bitrate: int = 100 * 1024,
        force: bool = False,
        progress_callback: Callable[[ProgressEvent], None] | None = None,
    ) -> JobResult:
        """Plan, preflight, and execute typed single- or two-pass compression."""
        if target_size_kb is not None and target_size_kb <= 0:
            raise ValueError("target_size_kb must be a positive integer")
        options = CompressOptions(
            target_size_bytes=target_size_kb * 1024 if target_size_kb is not None else None,
            crf=crf,
            two_pass=two_pass,
            video_codec=video_codec,
            audio_codec=audio_codec,
            video_bitrate=video_bitrate,
            audio_bitrate=audio_bitrate,
            preset=preset,
            pixel_format=pixel_format,
            threads=threads,
            container_overhead_percent=container_overhead_percent,
            minimum_video_bitrate=minimum_video_bitrate,
        )
        return self._run_workflow(
            self.planner.compress(input_file, output_file, options, force=force),
            progress_callback=progress_callback,
        )

    def extract_audio(
        self,
        input_file: str,
        output_file: str,
        *,
        audio_codec: str | None = None,
        audio_bitrate: str = "192k",
        sample_rate: int | None = None,
        channels: int | None = None,
        threads: int | None = None,
        force: bool = False,
        progress_callback: Callable[[ProgressEvent], None] | None = None,
    ) -> JobResult:
        """Plan, preflight, and execute typed audio extraction."""
        plan = self.planner.extract_audio(
            input_file,
            output_file,
            audio_codec=audio_codec,
            audio_bitrate=audio_bitrate,
            sample_rate=sample_rate,
            channels=channels,
            threads=threads,
            force=force,
        )
        return self._run_workflow(plan, progress_callback=progress_callback)

    def extract_thumbnail(
        self,
        input_file: str,
        output_file: str,
        timestamp: str = "00:00:01",
        width: int = 320,
        height: int | None = None,
        quality: int = 2,
        *,
        force: bool = False,
        progress_callback: Callable[[ProgressEvent], None] | None = None,
    ) -> JobResult:
        """Plan, preflight, and execute typed thumbnail extraction."""
        plan = self.planner.thumbnail(
            input_file,
            output_file,
            timestamp=timestamp,
            width=width,
            height=height,
            quality=quality,
            force=force,
        )
        return self._run_workflow(plan, progress_callback=progress_callback)

    def adjust_speed(
        self,
        input_file: str,
        output_file: str,
        speed_factor: float = 1.0,
        audio_pitch: bool = True,
        *,
        force: bool = False,
        progress_callback: Callable[[ProgressEvent], None] | None = None,
    ) -> JobResult:
        """Plan, preflight, and execute typed video speed adjustment."""
        plan = self.planner.speed(
            "video",
            input_file,
            output_file,
            factor=speed_factor,
            preserve_pitch=audio_pitch,
            force=force,
        )
        return self._run_workflow(plan, progress_callback=progress_callback)

    def generate_waveform(
        self,
        input_file: str,
        output_file: str,
        width: int = 800,
        height: int = 200,
        colors: str = "white",
        *,
        force: bool = False,
        progress_callback: Callable[[ProgressEvent], None] | None = None,
    ) -> JobResult:
        """Plan, preflight, and execute typed waveform rendering."""
        plan = self.planner.waveform(
            input_file,
            output_file,
            width=width,
            height=height,
            colors=colors,
            force=force,
        )
        return self._run_workflow(plan, progress_callback=progress_callback)

    def get_version(self) -> str:
        """Return the FFmpeg version banner line."""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(f"FFmpeg executable '{self.ffmpeg_path}' was not found.") from exc
        return result.stdout.splitlines()[0]

    def _annotate_failure(
        self,
        command: list[str],
        result: subprocess.CompletedProcess[str],
    ) -> subprocess.CompletedProcess[str]:
        if result.returncode == 0:
            return result
        command_text = shlex.join(command)
        details = result.stderr.strip() or "FFmpeg did not provide stderr output."
        return subprocess.CompletedProcess(
            args=result.args,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=f"FFmpeg command failed with exit code {result.returncode}.\nCommand: {command_text}\n{details}",
        )
