"""
Progress tracking for FFmpeg operations.
"""

import subprocess
import threading
from typing import Callable, Dict, Any, Optional
import re


class ProgressTracker:
    """
    Tracks FFmpeg progress by parsing progress output.
    """

    def __init__(self, callback: Callable[[Dict[str, Any]], None], use_pipe: bool = True):
        """
        Initialize the progress tracker.

        Args:
            callback: Function to call with progress updates
            use_pipe: If True, use -progress pipe:1 for robust parsing.
                     If False, fall back to stderr parsing.
        """
        self.callback = callback
        self.progress = {}
        self.use_pipe = use_pipe

    def run(self, cmd: list) -> subprocess.CompletedProcess:
        """
        Run a command and track progress.

        Args:
            cmd: Command to run

        Returns:
            CompletedProcess instance
        """
        if self.use_pipe:
            return self._run_with_pipe(cmd)
        else:
            return self._run_with_stderr(cmd)

    def _run_with_pipe(self, cmd: list) -> subprocess.CompletedProcess:
        """
        Run FFmpeg with -progress pipe:1 for robust progress parsing.
        """
        # Add progress options to command
        progress_cmd = cmd + ["-progress", "pipe:1", "-nostats", "-loglevel", "error"]

        process = subprocess.Popen(
            progress_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Read progress from stdout
        progress_thread = threading.Thread(target=self._read_progress_pipe, args=(process.stdout,))
        progress_thread.daemon = True
        progress_thread.start()

        # Wait for process to complete
        _, stderr = process.communicate()

        # Wait for progress thread to finish
        progress_thread.join(timeout=1.0)

        return subprocess.CompletedProcess(
            cmd, process.returncode, "", stderr
        )

    def _run_with_stderr(self, cmd: list) -> subprocess.CompletedProcess:
        """
        Fallback: Run FFmpeg and parse stderr for progress (legacy method).
        """
        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Start a thread to read stderr
        stderr_thread = threading.Thread(target=self._read_stderr, args=(process.stderr,))
        stderr_thread.daemon = True
        stderr_thread.start()

        # Wait for process to complete
        stdout, _ = process.communicate()

        # Wait for stderr thread to finish
        stderr_thread.join(timeout=1.0)

        return subprocess.CompletedProcess(
            cmd, process.returncode, stdout, ""
        )

    def _read_progress_pipe(self, stdout_pipe):
        """
        Read from stdout pipe (progress output) and parse progress information.
        """
        while True:
            line = stdout_pipe.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            # Parse key=value progress line
            progress = self._parse_progress_pipe_line(line)
            if progress:
                self.progress.update(progress)
                # Call callback with current progress
                self.callback(self.progress.copy())

    def _read_stderr(self, stderr_pipe):
        """
        Read from stderr pipe and parse progress information (fallback method).
        """
        while True:
            line = stderr_pipe.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            # Parse progress line
            progress = self._parse_progress_line(line)
            if progress:
                self.progress.update(progress)
                # Call callback with current progress
                self.callback(self.progress.copy())

    def _parse_progress_pipe_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single key=value line from FFmpeg -progress pipe:1 output.

        Args:
            line: A line from FFmpeg stdout (key=value format)

        Returns:
            Dictionary with parsed progress data or None
        """
        line = line.strip()
        if '=' not in line:
            return None

        key, value = line.split('=', 1)

        def with_status(payload: Dict[str, Any]) -> Dict[str, Any]:
            payload.setdefault("status", "progress")
            return payload

        # Convert values based on key
        if key == "frame":
            if value != "N/A":
                return with_status({"frame": int(value)})
        elif key == "fps":
            if value != "N/A":
                return with_status({"fps": float(value)})
        elif key == "bitrate":
            # Remove 'kbits/s' suffix
            if value != "N/A":
                return with_status({"bitrate_kbps": float(value.replace('kbits/s', ''))})
        elif key == "total_size":
            if value != "N/A":
                return with_status({"size_kb": int(value) / 1024})  # Convert bytes to KB
        elif key in ("out_time", "out_time_ms", "out_time_us"):
            if value == "N/A":
                return None
            if key == "out_time_us":
                secs = float(value) / 1_000_000
            elif key == "out_time_ms":
                # FFmpeg's pipe output labels this field as milliseconds, but in
                # practice the value is emitted in microseconds.
                secs = float(value) / 1_000_000
            else:
                secs = self._time_to_seconds(value)
            return with_status({"time_seconds": secs})
        elif key == "speed":
            if value != "N/A":
                return with_status({"speed": float(value.replace('x', ''))})
        elif key == "progress":
            if value == "end":
                return {"status": "end"}
            return {"status": "progress"}

        return None

    def _parse_progress_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single line of FFmpeg progress output (fallback method).

        Args:
            line: A line from FFmpeg stderr

        Returns:
            Dictionary with parsed progress data or None
        """
        # FFmpeg progress lines look like: "frame=  123 fps=25.0 q=28.0 size=   12345kB time=00:00:05.00 bitrate=1234.5kbits/s speed=1.25x"
        progress_pattern = re.compile(
            r'frame=\s*(\d+)\s+fps=\s*([\d.]+)\s+.*?'
            r'size=\s*([\d.]+)kB\s+time=\s*([\d:.]+)\s+'
            r'bitrate=\s*([\d.]+)kbits/s\s+speed=\s*([\d.]+)x'
        )

        match = progress_pattern.search(line)
        if match:
            frame, fps, size_kb, time_str, bitrate_kbps, speed = match.groups()

            # Convert time string (HH:MM:SS.ms) to seconds
            time_seconds = self._time_to_seconds(time_str)

            return {
                "frame": int(frame),
                "fps": float(fps),
                "size_kb": float(size_kb),
                "time_seconds": time_seconds,
                "bitrate_kbps": float(bitrate_kbps),
                "speed": float(speed),
                "status": "progress"
            }

        # Check for completion
        if "progress=end" in line:
            return {"status": "end"}

        return None

    def _time_to_seconds(self, time_str: str) -> float:
        """
        Convert FFmpeg time string to seconds.

        Args:
            time_str: Time in format HH:MM:SS.ms

        Returns:
            Time in seconds
        """
        parts = time_str.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        elif len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        else:
            return float(time_str)

    @staticmethod
    def simple_progress_callback(progress: Dict[str, Any]):
        """
        A simple progress callback that prints progress to console.

        Args:
            progress: Progress dictionary
        """
        if progress.get("status") == "end":
            print("Conversion completed!")
        elif "frame" in progress:
            frame = progress.get("frame", 0)
            fps = progress.get("fps", 0)
            time_sec = progress.get("time_seconds", 0)
            speed = progress.get("speed", 0)

            # Format time
            minutes = int(time_sec // 60)
            seconds = int(time_sec % 60)
            time_str = f"{minutes:02d}:{seconds:02d}"

            print(f"Frame: {frame}, FPS: {fps:.1f}, Time: {time_str}, Speed: {speed:.2f}x")


class ProgressCallback:
    """
    A helper class for creating progress callbacks with context.
    """

    def __init__(self, total_duration: Optional[float] = None):
        """
        Initialize progress callback helper.

        Args:
            total_duration: Total duration in seconds for percentage calculation
        """
        self.total_duration = total_duration

    def __call__(self, progress: Dict[str, Any]):
        """
        Progress callback that can calculate percentage if duration is known.
        """
        if progress.get("status") == "end":
            print("100% - Conversion completed!")
        elif "time_seconds" in progress and self.total_duration:
            current_time = progress["time_seconds"]
            percentage = min(100.0, (current_time / self.total_duration) * 100)
            print(f"{percentage:.1f}% - {progress}")
        else:
            print(f"Progress: {progress}")
