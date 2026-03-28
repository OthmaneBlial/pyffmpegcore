"""
FFmpeg command execution and helper methods.
"""

from __future__ import annotations

import glob
import os
import subprocess
from typing import Callable, List, Optional

from .progress import ProgressTracker


def escape_path_for_filter(path: str) -> str:
    """
    Escape a file path for use in FFmpeg filter strings.
    """
    escaped = path.replace("\\", "/")
    return escaped.replace("'", "\\'")


def escape_path_for_concat(path: str) -> str:
    """
    Escape a file path for use in FFmpeg concat files.
    """
    escaped = path.replace("'", "\\'")
    return f"'{escaped}'"


class FFmpegRunner:
    """
    Execute FFmpeg commands and expose helper methods for common workflows.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def run(
        self,
        args: List[str],
        progress_callback: Optional[Callable] = None,
    ) -> subprocess.CompletedProcess:
        """
        Run FFmpeg with the provided argument list.
        """
        cmd = [self.ffmpeg_path] + args

        try:
            if progress_callback is not None:
                result = ProgressTracker(progress_callback).run(cmd)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"FFmpeg executable '{self.ffmpeg_path}' was not found. "
                "Install FFmpeg or pass a valid ffmpeg_path."
            ) from exc

        return self._annotate_failure(cmd, result)

    def run_with_progress(
        self,
        args: List[str],
        show_percentage: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Run FFmpeg and print lightweight progress updates.
        """

        def progress_callback(progress: dict) -> None:
            if progress.get("status") == "end":
                print("\rProgress: complete", flush=True)
                return

            if show_percentage and "time_seconds" in progress:
                print(
                    f"\rProgress time: {progress['time_seconds']:.2f}s",
                    end="",
                    flush=True,
                )
            elif "frame" in progress:
                print(
                    f"\rFrame: {progress['frame']}",
                    end="",
                    flush=True,
                )

        return self.run(args, progress_callback)

    def convert(
        self,
        input_file: str,
        output_file: str,
        progress_callback=None,
        audio_only: bool = False,
        hwaccel=None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        """
        Convert a video or audio file to another format.
        """
        args: List[str] = []

        if hwaccel:
            args.extend(["-hwaccel", hwaccel])

        args.extend(["-i", input_file])

        if audio_only:
            args.append("-vn")

        video_codec = kwargs.get("video_codec")
        if video_codec and not audio_only:
            args.extend(["-c:v", video_codec])

        audio_codec = kwargs.get("audio_codec")
        if audio_codec:
            args.extend(["-c:a", audio_codec])

        if "video_bitrate" in kwargs and not audio_only:
            args.extend(["-b:v", kwargs["video_bitrate"]])
        if "audio_bitrate" in kwargs:
            args.extend(["-b:a", kwargs["audio_bitrate"]])

        if not audio_only and video_codec != "copy":
            args.extend(["-pix_fmt", kwargs.get("pix_fmt", "yuv420p")])

        self._append_threads(args, kwargs)
        self._append_movflags(args, output_file, kwargs)

        args.extend(["-y", output_file])
        return self.run(args, progress_callback)

    def resize(
        self,
        input_file: str,
        output_file: str,
        width: int,
        height: int,
        progress_callback=None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        """
        Resize a video to the specified dimensions.
        """
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive integers")

        args = ["-i", input_file, "-vf", f"scale={width}:{height}"]

        video_codec = kwargs.get("video_codec")
        audio_codec = kwargs.get("audio_codec")
        if video_codec:
            args.extend(["-c:v", video_codec])
        if audio_codec:
            args.extend(["-c:a", audio_codec])

        if video_codec != "copy":
            args.extend(["-pix_fmt", kwargs.get("pix_fmt", "yuv420p")])

        self._append_threads(args, kwargs)
        self._append_movflags(args, output_file, kwargs)

        args.extend(["-y", output_file])
        return self.run(args, progress_callback)

    def compress(
        self,
        input_file: str,
        output_file: str,
        target_size_kb: int = None,
        crf: int = 23,
        two_pass: bool = True,
        progress_callback=None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        """
        Compress a video file.
        """
        if target_size_kb is not None and target_size_kb <= 0:
            raise ValueError("target_size_kb must be a positive integer")
        if not 0 <= crf <= 51:
            raise ValueError("crf must be between 0 and 51")

        if target_size_kb and two_pass:
            return self._compress_two_pass(
                input_file,
                output_file,
                target_size_kb,
                progress_callback,
                **kwargs,
            )

        return self._compress_single_pass(
            input_file,
            output_file,
            crf,
            progress_callback,
            **kwargs,
        )

    def _compress_single_pass(
        self,
        input_file: str,
        output_file: str,
        crf: int,
        progress_callback=None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        args = ["-i", input_file]

        video_codec = kwargs.get("video_codec", "libx264")
        args.extend(["-c:v", video_codec])

        if video_codec != "copy":
            if "video_bitrate" in kwargs:
                args.extend(["-b:v", kwargs["video_bitrate"]])
            else:
                args.extend(["-crf", str(crf)])
            args.extend(["-preset", kwargs.get("preset", "medium")])
            args.extend(["-pix_fmt", kwargs.get("pix_fmt", "yuv420p")])

        args.extend(["-c:a", kwargs.get("audio_codec", "aac")])
        if "audio_bitrate" in kwargs:
            args.extend(["-b:a", kwargs["audio_bitrate"]])

        self._append_threads(args, kwargs)
        self._append_movflags(args, output_file, kwargs)

        args.extend(["-y", output_file])
        return self.run(args, progress_callback)

    def _compress_two_pass(
        self,
        input_file: str,
        output_file: str,
        target_size_kb: int,
        progress_callback=None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        video_codec = kwargs.get("video_codec", "libx264")
        if video_codec == "copy":
            raise ValueError(
                "video_codec='copy' is not supported with two-pass compression. "
                "Use single-pass compression instead."
            )

        from .probe import FFprobeRunner

        metadata = FFprobeRunner().probe(input_file)
        duration = metadata.get("duration", 60) or 60
        audio_bitrate = kwargs.get("audio_bitrate", "128k")

        audio_bitrate_bps = self._parse_bitrate(audio_bitrate)
        total_audio_kb = (audio_bitrate_bps * duration) / (8 * 1024)

        overhead_pct = kwargs.get("overhead_pct", 1.0)
        container_overhead_kb = target_size_kb * (overhead_pct / 100.0)
        available_kb = target_size_kb - total_audio_kb - container_overhead_kb

        if available_kb <= 0:
            raise ValueError(
                f"Target size {target_size_kb}KB too small for {duration:.1f}s "
                f"video with {audio_bitrate} audio"
            )

        min_video_bitrate_bps = 100 * 1024
        video_bitrate_bps = max(
            min_video_bitrate_bps,
            int((available_kb * 8 * 1024) / duration),
        )
        video_bitrate = f"{video_bitrate_bps // 1024}k"

        preset = kwargs.get("preset", "medium")
        passlog = f"{output_file}.pass"

        pass1_args = [
            "-i",
            input_file,
            "-c:v",
            video_codec,
            "-b:v",
            video_bitrate,
            "-preset",
            preset,
            "-pass",
            "1",
            "-passlogfile",
            passlog,
            "-an",
            "-f",
            "null",
            os.devnull,
        ]
        self._append_threads(pass1_args, kwargs)

        result1 = self.run(pass1_args)
        if result1.returncode != 0:
            self._cleanup_pass_logs(output_file)
            return result1

        pass2_args = [
            "-i",
            input_file,
            "-c:v",
            video_codec,
            "-b:v",
            video_bitrate,
            "-preset",
            preset,
            "-pass",
            "2",
            "-passlogfile",
            passlog,
            "-pix_fmt",
            kwargs.get("pix_fmt", "yuv420p"),
            "-c:a",
            kwargs.get("audio_codec", "aac"),
        ]

        if "audio_bitrate" in kwargs:
            pass2_args.extend(["-b:a", kwargs["audio_bitrate"]])

        self._append_threads(pass2_args, kwargs)
        self._append_movflags(pass2_args, output_file, kwargs)

        pass2_args.extend(["-y", output_file])
        result2 = self.run(pass2_args, progress_callback)

        self._cleanup_pass_logs(output_file)
        return result2

    def _parse_bitrate(self, bitrate_str: str) -> int:
        """
        Parse bitrate strings such as '128k' or '2M' to bits per second.
        """
        if bitrate_str.endswith("k"):
            return int(bitrate_str[:-1]) * 1024
        if bitrate_str.endswith("M"):
            return int(float(bitrate_str[:-1]) * 1024 * 1024)
        return int(bitrate_str)

    def _cleanup_pass_logs(self, output_file: str):
        """
        Remove FFmpeg two-pass log files.
        """
        patterns = [
            f"{output_file}.pass",
            f"{output_file}.pass-0.log",
            f"{output_file}.pass-0.log.mbtree",
            f"{output_file}.pass-0.log.temp",
            f"{output_file}.pass*",
        ]

        for pattern in patterns:
            for filepath in glob.glob(pattern):
                try:
                    os.remove(filepath)
                except OSError:
                    pass

    def extract_audio(
        self,
        input_file: str,
        output_file: str,
        progress_callback=None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        """
        Extract audio from a media file.
        """
        args = ["-i", input_file, "-vn"]

        audio_codec = kwargs.get("audio_codec", self._default_audio_codec(output_file))
        args.extend(["-c:a", audio_codec])
        if "audio_bitrate" in kwargs and audio_codec != "copy":
            args.extend(["-b:a", kwargs["audio_bitrate"]])
        if "sample_rate" in kwargs:
            args.extend(["-ar", str(kwargs["sample_rate"])])
        if "channels" in kwargs:
            args.extend(["-ac", str(kwargs["channels"])])

        self._append_threads(args, kwargs)

        args.extend(["-y", output_file])
        return self.run(args, progress_callback)

    def extract_thumbnail(
        self,
        input_file: str,
        output_file: str,
        timestamp: str = "00:00:01",
        width: int = 320,
        height: int = None,
        quality: int = 2,
    ) -> subprocess.CompletedProcess:
        """
        Extract a thumbnail from a video at a specific timestamp.
        """
        if width <= 0:
            raise ValueError("width must be a positive integer")
        if height is not None and height <= 0:
            raise ValueError("height must be a positive integer when provided")
        if not 1 <= quality <= 31:
            raise ValueError("quality must be between 1 and 31")

        scale_filter = f"scale={width}:-1" if height is None else f"scale={width}:{height}"
        args = [
            "-i",
            input_file,
            "-ss",
            timestamp,
            "-vframes",
            "1",
            "-vf",
            scale_filter,
            "-q:v",
            str(quality),
            "-y",
            output_file,
        ]
        return self.run(args)

    def adjust_speed(
        self,
        input_file: str,
        output_file: str,
        speed_factor: float = 1.0,
        audio_pitch: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Adjust playback speed for a media file with video and audio streams.
        """
        if speed_factor <= 0:
            raise ValueError("speed_factor must be positive")

        vf_filters = []
        af_filters = []

        if speed_factor != 1.0:
            vf_filters.append(f"setpts={1 / speed_factor}*PTS")
            if audio_pitch:
                af_filters.append(self._build_atempo_chain(speed_factor))
            else:
                af_filters.append(f"asetrate=44100*{speed_factor},aresample=44100")

        args = ["-i", input_file]
        if vf_filters:
            args.extend(["-vf", ",".join(vf_filters)])
        if af_filters:
            args.extend(["-af", ",".join(af_filters)])

        args.extend(["-c:v", "libx264", "-c:a", "aac", "-y", output_file])
        return self.run(args)

    def generate_waveform(
        self,
        input_file: str,
        output_file: str,
        width: int = 800,
        height: int = 200,
        colors: str = "white",
    ) -> subprocess.CompletedProcess:
        """
        Generate a waveform image from an audio stream.
        """
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive integers")

        args = [
            "-i",
            input_file,
            "-filter_complex",
            f"[0:a]showwavespic=s={width}x{height}:colors={colors}[waveform]",
            "-map",
            "[waveform]",
            "-frames:v",
            "1",
            "-y",
            output_file,
        ]
        return self.run(args)

    def _build_atempo_chain(self, speed_factor: float) -> str:
        """
        Build an atempo filter chain for arbitrary positive speed factors.
        """
        if 0.5 <= speed_factor <= 2.0:
            return f"atempo={speed_factor}"

        factors = []
        current = speed_factor

        while current > 2.0:
            factors.append(2.0)
            current /= 2.0

        while current < 0.5:
            factors.append(0.5)
            current /= 0.5

        if current != 1.0:
            factors.append(current)

        return ",".join(f"atempo={factor}" for factor in factors)

    def _default_audio_codec(self, output_file: str) -> str:
        """
        Pick a default audio codec based on the output extension.
        """
        extension = os.path.splitext(output_file)[1].lower()
        codec_by_extension = {
            ".aac": "aac",
            ".flac": "flac",
            ".m4a": "aac",
            ".mp3": "libmp3lame",
            ".ogg": "libvorbis",
            ".opus": "libopus",
            ".wav": "pcm_s16le",
        }
        return codec_by_extension.get(extension, "aac")

    def _append_threads(self, args: List[str], kwargs: dict) -> None:
        if "threads" in kwargs:
            args.extend(["-threads", str(kwargs["threads"])])

    def _append_movflags(self, args: List[str], output_file: str, kwargs: dict) -> None:
        movflags = kwargs.get("movflags", "+faststart")
        if output_file.endswith((".mp4", ".m4v")) and movflags:
            args.extend(["-movflags", movflags])

    def _annotate_failure(
        self,
        cmd: List[str],
        result: subprocess.CompletedProcess,
    ) -> subprocess.CompletedProcess:
        if result.returncode == 0:
            return result

        stderr = (result.stderr or "").strip()
        prefix = f"FFmpeg command failed with exit code {result.returncode}."
        command = " ".join(cmd)
        annotated_stderr = f"{prefix}\nCommand: {command}"
        if stderr:
            annotated_stderr = f"{annotated_stderr}\n{stderr}"

        return subprocess.CompletedProcess(
            result.args if hasattr(result, "args") else cmd,
            result.returncode,
            getattr(result, "stdout", ""),
            annotated_stderr,
        )

    def get_version(self) -> str:
        """
        Return the FFmpeg version banner line.
        """
        result = subprocess.run(
            [self.ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.split("\n")[0]
        raise RuntimeError(f"Failed to get FFmpeg version: {result.stderr}")
