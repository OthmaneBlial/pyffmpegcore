"""
FFmpeg command execution and helper methods.
"""

import subprocess
import os
from typing import List, Optional, Callable, Dict, Any
from .progress import ProgressTracker

import subprocess
import os
from typing import List, Optional, Callable, Dict, Any
from .progress import ProgressTracker


def escape_path_for_filter(path: str) -> str:
    """
    Escape a file path for use in FFmpeg filter strings.

    Handles backslashes for Windows and other special characters.

    Args:
        path: File path to escape

    Returns:
        Escaped path string
    """
    # Replace backslashes with forward slashes for Windows compatibility
    escaped = path.replace('\\', '/')
    # Escape single quotes by replacing with '\''
    escaped = escaped.replace("'", "\\'")
    return escaped


def escape_path_for_concat(path: str) -> str:
    """
    Escape a file path for use in FFmpeg concat files.

    Args:
        path: File path to escape

    Returns:
        Escaped path string
    """
    # For concat files, wrap in single quotes and escape internal single quotes
    escaped = path.replace("'", "\\'")
    return f"'{escaped}'"

class FFmpegRunner:
    """
    A runner for executing FFmpeg commands with helper methods for common tasks.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """
        Initialize the FFmpeg runner.

        Args:
            ffmpeg_path: Path to the ffmpeg executable. Defaults to "ffmpeg".
        """
        self.ffmpeg_path = ffmpeg_path

    def run(self, args: List[str], progress_callback: Optional[Callable] = None) -> subprocess.CompletedProcess:
        """
        Run an FFmpeg command with the given arguments.

        Args:
            args: List of command line arguments for ffmpeg
            progress_callback: Optional callback function for progress updates.
                              Uses robust -progress pipe:1 parsing when provided.

        Returns:
            CompletedProcess instance
        """
        cmd = [self.ffmpeg_path] + args

        if progress_callback:
            # Use progress tracker to parse stderr
            tracker = ProgressTracker(progress_callback)
            return tracker.run(cmd)
        else:
            return subprocess.run(cmd, capture_output=True, text=True)

    def run_with_progress(self, args: List[str], show_percentage: bool = True) -> subprocess.CompletedProcess:
        """
        Run an FFmpeg command with progress display.

        Args:
            args: List of command line arguments for ffmpeg
            show_percentage: If True, display progress percentage

        Returns:
            CompletedProcess instance
        """
        if show_percentage:
            def progress_callback(progress):
                if 'percentage' in progress:
                    print(f"\rProgress: {progress['percentage']:.1f}%", end='', flush=True)
            return self.run(args, progress_callback)
        else:
            return self.run(args)

    def convert(self, input_file: str, output_file: str, progress_callback=None, audio_only=False, hwaccel=None, **kwargs) -> subprocess.CompletedProcess:
        """
        Convert a video/audio file to another format.

        Args:
            input_file: Path to input file
            output_file: Path to output file
            progress_callback: Optional callback for progress updates
            audio_only: If True, extract only audio (no video processing)
            hwaccel: Hardware acceleration (e.g., 'auto', 'cuda', 'qsv')
            **kwargs: Additional ffmpeg options (e.g., video_codec='libx264', audio_codec='aac')

        Returns:
            CompletedProcess instance
        """
        args = []

        # Hardware acceleration
        if hwaccel:
            args.extend(["-hwaccel", hwaccel])

        args.extend(["-i", input_file])

        # Audio-only mode
        if audio_only:
            args.append("-vn")  # No video

        # Add common options
        if "video_codec" in kwargs and not audio_only:
            args.extend(["-c:v", kwargs["video_codec"]])
        if "audio_codec" in kwargs:
            args.extend(["-c:a", kwargs["audio_codec"]])
        if "video_bitrate" in kwargs and not audio_only:
            args.extend(["-b:v", kwargs["video_bitrate"]])
        if "audio_bitrate" in kwargs:
            args.extend(["-b:a", kwargs["audio_bitrate"]])

        # Add pixel format for video compatibility (allow override, skip for copy)
        video_codec = kwargs.get("video_codec")
        if not audio_only and video_codec != "copy":
            pix_fmt = kwargs.get("pix_fmt", "yuv420p")
            args.extend(["-pix_fmt", pix_fmt])

        # Threads
        if "threads" in kwargs:
            args.extend(["-threads", str(kwargs["threads"])])

        # Fast start for MP4 files
        if output_file.endswith(('.mp4', '.m4v')):
            args.extend(["-movflags", "+faststart"])

        args.extend(["-y", output_file])  # -y to overwrite output files
        return self.run(args, progress_callback)

    def resize(self, input_file: str, output_file: str, width: int, height: int,
               progress_callback=None, **kwargs) -> subprocess.CompletedProcess:
        """
        Resize a video to the specified dimensions.

        Args:
            input_file: Path to input file
            output_file: Path to output file
            width: Target width
            height: Target height
            progress_callback: Optional callback for progress updates
            **kwargs: Additional options

        Returns:
            CompletedProcess instance
        """
        args = ["-i", input_file, "-vf", f"scale={width}:{height}"]

        # Add common options
        if "video_codec" in kwargs:
            args.extend(["-c:v", kwargs["video_codec"]])
        if "audio_codec" in kwargs:
            args.extend(["-c:a", kwargs["audio_codec"]])

        # Pixel format for compatibility (allow override)
        pix_fmt = kwargs.get("pix_fmt", "yuv420p")
        args.extend(["-pix_fmt", pix_fmt])

        # Fast start for MP4 files
        if output_file.endswith(('.mp4', '.m4v')):
            args.extend(["-movflags", "+faststart"])

        # Threads
        if "threads" in kwargs:
            args.extend(["-threads", str(kwargs["threads"])])

        args.extend(["-y", output_file])
        return self.run(args, progress_callback)

    def compress(self, input_file: str, output_file: str, target_size_kb: int = None,
                 crf: int = 23, two_pass: bool = True, progress_callback=None, **kwargs) -> subprocess.CompletedProcess:
        """
        Compress a video file.

        Args:
            input_file: Path to input file
            output_file: Path to output file
            target_size_kb: Target file size in KB (approximate, requires two_pass=True)
            crf: Constant Rate Factor (0-51, lower = higher quality, ignored if target_size_kb set)
            two_pass: Use two-pass encoding for better quality at target size
            progress_callback: Optional callback for progress updates
            **kwargs: Additional options (audio_bitrate, preset, etc.)

        Returns:
            CompletedProcess instance
        """
        if target_size_kb and two_pass:
            return self._compress_two_pass(input_file, output_file, target_size_kb, progress_callback, **kwargs)
        else:
            return self._compress_single_pass(input_file, output_file, crf, progress_callback, **kwargs)

    def _compress_single_pass(self, input_file: str, output_file: str, crf: int, progress_callback=None, **kwargs) -> subprocess.CompletedProcess:
        """Single-pass compression using CRF."""
        args = ["-i", input_file]

        # Video codec and quality
        video_codec = kwargs.get("video_codec", "libx264")
        args.extend(["-c:v", video_codec])

        # Skip encoding parameters if copying video
        if video_codec != "copy":
            # Use bitrate mode if specified, otherwise CRF
            if "video_bitrate" in kwargs:
                args.extend(["-b:v", kwargs["video_bitrate"]])
            else:
                args.extend(["-crf", str(crf)])

            # Preset for encoding speed vs compression efficiency
            preset = kwargs.get("preset", "medium")
            args.extend(["-preset", preset])

            # Pixel format for compatibility (allow override)
            pix_fmt = kwargs.get("pix_fmt", "yuv420p")
            args.extend(["-pix_fmt", pix_fmt])

        # Audio codec
        audio_codec = kwargs.get("audio_codec", "aac")
        args.extend(["-c:a", audio_codec])

        # Audio bitrate
        if "audio_bitrate" in kwargs:
            args.extend(["-b:a", kwargs["audio_bitrate"]])

        # Fast start for web playback
        if output_file.endswith(('.mp4', '.m4v')):
            args.extend(["-movflags", "+faststart"])

        # Threads
        if "threads" in kwargs:
            args.extend(["-threads", str(kwargs["threads"])])

        args.extend(["-y", output_file])
        return self.run(args, progress_callback)

    def _compress_two_pass(self, input_file: str, output_file: str, target_size_kb: int, progress_callback=None, **kwargs) -> subprocess.CompletedProcess:
        """Two-pass compression for accurate target file size."""
        # Two-pass requires re-encoding, so forbid copy codec
        video_codec = kwargs.get("video_codec", "libx264")
        if video_codec == "copy":
            raise ValueError("video_codec='copy' is not supported with two-pass compression. Use single-pass compression instead.")

        # Get input duration and audio info
        from .probe import FFprobeRunner
        ffprobe = FFprobeRunner()
        metadata = ffprobe.probe(input_file)

        duration = metadata.get("duration", 60)  # fallback to 60 seconds
        audio_bitrate = kwargs.get("audio_bitrate", "128k")

        # Calculate video bitrate (rough approximation)
        # Account for container overhead (~1%) and audio
        audio_bitrate_bps = self._parse_bitrate(audio_bitrate)
        total_audio_bits = audio_bitrate_bps * duration
        total_audio_kb = total_audio_bits / (8 * 1024)

        # Add configurable container overhead (default 1%)
        overhead_pct = kwargs.get("overhead_pct", 1.0)
        container_overhead_kb = target_size_kb * (overhead_pct / 100.0)
        available_kb = target_size_kb - total_audio_kb - container_overhead_kb

        if available_kb <= 0:
            raise ValueError(f"Target size {target_size_kb}KB too small for {duration:.1f}s video with {audio_bitrate} audio")

        # Ensure minimum reasonable bitrate (100 kbps)
        min_video_bitrate_bps = 100 * 1024
        video_bitrate_bps = max(min_video_bitrate_bps, int((available_kb * 8 * 1024) / duration))
        video_bitrate_kbps = video_bitrate_bps // 1024  # Convert to kbps for FFmpeg
        video_bitrate = f"{video_bitrate_kbps}k"

        import os

        # Get options from kwargs
        audio_codec = kwargs.get("audio_codec", "aac")
        preset = kwargs.get("preset", "medium")
        pix_fmt = kwargs.get("pix_fmt", "yuv420p")
        video_codec = kwargs.get("video_codec", "libx264")

        # Pass 1: Analysis (no audio needed)
        pass1_args = ["-i", input_file, "-c:v", video_codec, "-b:v", video_bitrate,
                     "-preset", preset, "-pass", "1", "-passlogfile", f"{output_file}.pass",
                     "-an", "-f", "null", os.devnull]
        result1 = self.run(pass1_args)
        if result1.returncode != 0:
            # Clean up on failure
            self._cleanup_pass_logs(output_file)
            return result1

        # Pass 2: Encoding
        pass2_args = ["-i", input_file, "-c:v", video_codec, "-b:v", video_bitrate,
                     "-preset", preset, "-pass", "2", "-passlogfile", f"{output_file}.pass",
                     "-pix_fmt", pix_fmt, "-c:a", audio_codec]

        if "audio_bitrate" in kwargs:
            pass2_args.extend(["-b:a", kwargs["audio_bitrate"]])

        if output_file.endswith(('.mp4', '.m4v')):
            pass2_args.extend(["-movflags", "+faststart"])

        pass2_args.extend(["-y", output_file])
        result2 = self.run(pass2_args, progress_callback)

        # Clean up pass log files
        self._cleanup_pass_logs(output_file)

        return result2

    def _parse_bitrate(self, bitrate_str: str) -> int:
        """Parse bitrate string like '128k' to bits per second."""
        if bitrate_str.endswith('k'):
            return int(bitrate_str[:-1]) * 1024
        elif bitrate_str.endswith('M'):
            return int(float(bitrate_str[:-1]) * 1024 * 1024)
        else:
            return int(bitrate_str)

    def _cleanup_pass_logs(self, output_file: str):
        """Clean up all FFmpeg two-pass log files."""
        import os
        import glob

        # Common pass log file patterns
        patterns = [
            f"{output_file}.pass",
            f"{output_file}.pass-0.log",
            f"{output_file}.pass-0.log.mbtree",
            f"{output_file}.pass-0.log.temp",
        ]

        # Also try glob pattern for any pass-related files
        glob_patterns = [
            f"{output_file}.pass*",
        ]

        for pattern in glob_patterns:
            for filepath in glob.glob(pattern):
                try:
                    os.remove(filepath)
                except OSError:
                    pass  # Ignore cleanup errors

        # Clean up specific known files
        for filepath in patterns:
            try:
                os.remove(filepath)
            except OSError:
                pass  # Ignore cleanup errors

    def extract_audio(self, input_file: str, output_file: str, progress_callback=None, **kwargs) -> subprocess.CompletedProcess:
        """
        Extract audio from a video file.

        Args:
            input_file: Path to input video file
            output_file: Path to output audio file
            progress_callback: Optional callback for progress updates
            **kwargs: Additional options (e.g., audio_codec='aac', audio_bitrate='128k')

        Returns:
            CompletedProcess instance
        """
        args = ["-i", input_file, "-vn"]  # -vn = no video

        audio_codec = kwargs.get("audio_codec", self._default_audio_codec(output_file))
        args.extend(["-c:a", audio_codec])
        if "audio_bitrate" in kwargs and audio_codec != "copy":
            args.extend(["-b:a", kwargs["audio_bitrate"]])
        if "sample_rate" in kwargs:
            args.extend(["-ar", str(kwargs["sample_rate"])])
        if "channels" in kwargs:
            args.extend(["-ac", str(kwargs["channels"])])
        if "threads" in kwargs:
            args.extend(["-threads", str(kwargs["threads"])])
        args.extend(["-y", output_file])
        return self.run(args, progress_callback)
    def extract_thumbnail(self, input_file: str, output_file: str, timestamp: str = "00:00:01",
                         width: int = 320, height: int = None, quality: int = 2) -> subprocess.CompletedProcess:
        """
        Extract a thumbnail from a video at a specific timestamp.

        Args:
            input_file: Path to input video file
            output_file: Path to save the thumbnail
            timestamp: Time position in HH:MM:SS format
            width: Thumbnail width in pixels
            height: Thumbnail height in pixels (maintains aspect ratio if None)
            quality: JPEG quality (1-31, lower = higher quality)

        Returns:
            CompletedProcess instance
        """
        vf_filters = [f"scale={width}:-1" if height is None else f"scale={width}:{height}"]

        args = [
            "-i", input_file,
            "-ss", timestamp,
            "-vframes", "1",
            "-vf", ",".join(vf_filters),
            "-q:v", str(quality),
            "-y", output_file
        ]

        return self.run(args)

    def adjust_speed(self, input_file: str, output_file: str, speed_factor: float = 1.0,
                    audio_pitch: bool = True) -> subprocess.CompletedProcess:
        """
        Adjust the playback speed of a video.

        Args:
            input_file: Path to input video file
            output_file: Path to output file
            speed_factor: Speed multiplier (e.g., 2.0 = 2x speed, 0.5 = half speed)
            audio_pitch: If True, maintain audio pitch when changing speed

        Returns:
            CompletedProcess instance
        """
        vf_filters = []
        af_filters = []

        if speed_factor != 1.0:
            vf_filters.append(f"setpts={1/speed_factor}*PTS")
            if audio_pitch:
                # Chain atempo filters to handle factors outside 0.5-2.0 range
                atempo_chain = self._build_atempo_chain(speed_factor)
                af_filters.append(atempo_chain)
            else:
                af_filters.append(f"atempo={speed_factor},asetrate=44100")

        args = ["-i", input_file]

        if vf_filters:
            args.extend(["-vf", ",".join(vf_filters)])
        if af_filters:
            args.extend(["-af", ",".join(af_filters)])

        args.extend(["-c:v", "libx264", "-c:a", "aac", "-y", output_file])
        return self.run(args)

    def generate_waveform(self, input_file: str, output_file: str, width: int = 800,
                         height: int = 200, colors: str = "white") -> subprocess.CompletedProcess:
        """
        Generate a waveform visualization from an audio file.

        Args:
            input_file: Path to input audio/video file
            output_file: Path to output waveform image
            width: Width of the waveform image
            height: Height of the waveform image
            colors: Color scheme for the waveform

        Returns:
            CompletedProcess instance
        """
        vf_filter = f"showwavespic=s={width}x{height}:colors={colors}"

        args = [
            "-i", input_file,
            "-vf", vf_filter,
            "-frames:v", "1",
            "-y", output_file
        ]

        return self.run(args)

    def _build_atempo_chain(self, speed_factor: float) -> str:
        """
        Build a chain of atempo filters to achieve the desired speed factor.

        Since atempo only supports 0.5-2.0, we chain multiple filters for factors outside this range.
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

        return ",".join(f"atempo={f}" for f in factors)

    def _default_audio_codec(self, output_file: str) -> str:
        """Pick a reasonable default audio codec based on the output extension."""
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

    def generate_waveform(self, input_file: str, output_file: str, width: int = 800,
                         height: int = 200, colors: str = "white") -> subprocess.CompletedProcess:
        """
        Generate a waveform visualization from an audio file.

        Args:
            input_file: Path to input audio/video file
            output_file: Path to output waveform image
            width: Width of the waveform image
            height: Height of the waveform image
            colors: Color scheme for the waveform

        Returns:
            CompletedProcess instance
        """
        vf_filter = f"showwavespic=s={width}x{height}:colors={colors}"

        args = [
            "-i", input_file,
            "-vf", vf_filter,
            "-frames:v", "1",
            "-y", output_file
        ]

        return self.run(args)

    def get_version(self) -> str:
        """
        Get the FFmpeg version.

        Returns:
            Version string
        """
        result = subprocess.run([self.ffmpeg_path, "-version"],
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.split('\n')[0]
        else:
            raise RuntimeError(f"Failed to get FFmpeg version: {result.stderr}")
