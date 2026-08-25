"""Shared typed workflow planning without media mutations or shell strings."""

from __future__ import annotations

import os
import re
from pathlib import Path

from .capabilities import requirements_for
from .domain import (
    CompressOptions,
    ConvertOptions,
    ExecutionPlan,
    ExecutionPolicy,
    ExecutionStep,
    OverwritePolicy,
    ResizeOptions,
    normalized_path,
)
from .errors import EnvironmentUnavailableError, ValidationError
from .probe import FFprobeRunner

_AUDIO_CODEC_BY_EXTENSION = {
    ".aac": "aac",
    ".flac": "flac",
    ".m4a": "aac",
    ".mp3": "libmp3lame",
    ".ogg": "libvorbis",
    ".opus": "libopus",
    ".wav": "pcm_s16le",
}
_BITRATELESS_CODECS = {"flac", "pcm_s16le"}
_SIZE_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([kmgt]?i?b)?\s*$", re.IGNORECASE)


def _planning_probe_failure(exc: RuntimeError) -> RuntimeError:
    """Categorize the rare workflows that need media facts while planning."""
    if "was not found" in str(exc):
        return EnvironmentUnavailableError(str(exc))
    return ValidationError(f"input cannot be inspected for planning: {exc}")


def parse_size(value: str) -> int:
    """Parse honest decimal or binary byte units such as 25MB or 25MiB."""
    match = _SIZE_PATTERN.match(value)
    if not match:
        raise ValidationError("size must use B, KB, MB, GB, TB, KiB, MiB, GiB, or TiB, for example 25MB")
    amount = float(match.group(1))
    unit = (match.group(2) or "B").upper()
    powers = {"B": 0, "KB": 1, "MB": 2, "GB": 3, "TB": 4, "KIB": 1, "MIB": 2, "GIB": 3, "TIB": 4}
    base = 1024 if "I" in unit else 1000
    result = int(amount * base ** powers[unit])
    if result <= 0:
        raise ValidationError("size must be positive")
    return result


def parse_bitrate(value: str) -> int:
    """Parse FFmpeg-style bitrates into bits per second."""
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([kKmMgG]?)\s*", value)
    if not match:
        raise ValidationError("bitrate must be a positive number with an optional k, M, or G suffix")
    multiplier = {"": 1, "k": 1_000, "m": 1_000_000, "g": 1_000_000_000}[match.group(2).lower()]
    result = int(float(match.group(1)) * multiplier)
    if result <= 0:
        raise ValidationError("bitrate must be positive")
    return result


def _human_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            rendered = f"{amount:.0f}" if unit == "B" else f"{amount:.1f}"
            return f"{rendered} {unit} ({value} bytes)"
        amount /= 1024
    return f"{value} bytes"


def _codec_requirements(*values: tuple[str, str | None]) -> tuple[str, ...]:
    return tuple(f"encoder:{codec}" for _kind, codec in values if codec and codec != "copy")


def _audio_output_args(output: str, bitrate: str, codec: str | None = None) -> tuple[list[str], str]:
    selected = codec or _AUDIO_CODEC_BY_EXTENSION.get(Path(output).suffix.lower(), "aac")
    args = ["-c:a", selected]
    if bitrate and selected not in _BITRATELESS_CODECS:
        args.extend(["-b:a", bitrate])
    return args, selected


def _atempo_chain(factor: float) -> str:
    if factor <= 0:
        raise ValidationError("speed factor must be positive")
    factors: list[float] = []
    current = factor
    while current > 2.0:
        factors.append(2.0)
        current /= 2.0
    while current < 0.5:
        factors.append(0.5)
        current /= 0.5
    if current != 1.0 or not factors:
        factors.append(current)
    return ",".join(f"atempo={value}" for value in factors)


def _escape_filter_path(path: str) -> str:
    return path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


class WorkflowPlanner:
    """Build deterministic plans used by CLI, Python, examples, and pipelines."""

    def __init__(self, *, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def _policy(self, *, force: bool, timeout_seconds: float | None = None) -> ExecutionPolicy:
        return ExecutionPolicy(
            overwrite=OverwritePolicy.REPLACE if force else OverwritePolicy.REFUSE,
            timeout_seconds=timeout_seconds,
        )

    def _plan(
        self,
        workflow: str,
        args: list[str],
        *,
        inputs: list[str],
        outputs: list[str],
        force: bool,
        timeout_seconds: float | None = None,
        capabilities: tuple[str, ...] = (),
        streams: tuple[str, ...] = (),
        operations: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
        metadata: dict[str, object] | None = None,
        steps: tuple[ExecutionStep, ...] = (),
    ) -> ExecutionPlan:
        global_options = (
            "-y" if force else "-n",
            "-nostdin",
            "-progress",
            "pipe:1",
            "-nostats",
        )
        command = (self.ffmpeg_path, *global_options, *args)
        structured_steps = tuple(
            ExecutionStep(step.name, (step.command[0], *global_options, *step.command[1:])) for step in steps
        )
        plan_metadata = {"structured_progress": True, **dict(metadata or {})}
        return ExecutionPlan(
            workflow=workflow,
            command=command,
            inputs=tuple(normalized_path(value) for value in inputs),
            outputs=tuple(normalized_path(value) for value in outputs),
            policy=self._policy(force=force, timeout_seconds=timeout_seconds),
            required_capabilities=requirements_for(workflow, capabilities),
            selected_streams=streams,
            operations=operations,
            warnings=warnings,
            metadata=plan_metadata,
            steps=structured_steps,
        )

    def convert(
        self,
        input_file: str,
        output_file: str,
        options: ConvertOptions | None = None,
        *,
        force: bool = False,
        timeout_seconds: float | None = None,
    ) -> ExecutionPlan:
        options = options or ConvertOptions()
        source, output = normalized_path(input_file), normalized_path(output_file)
        args: list[str] = []
        if options.hardware_acceleration:
            args.extend(["-hwaccel", options.hardware_acceleration])
        args.extend(["-i", source])
        if options.audio_only:
            args.extend(["-map", "0:a:0", "-vn"])
        else:
            args.extend(["-map", "0:v:0?", "-map", "0:a:0?"])
        args.extend(["-map_metadata", "0", "-map_chapters", "0"])
        if options.video_codec and not options.audio_only:
            args.extend(["-c:v", options.video_codec])
        if options.audio_codec:
            args.extend(["-c:a", options.audio_codec])
        if options.video_bitrate and not options.audio_only:
            args.extend(["-b:v", options.video_bitrate])
        if options.audio_bitrate:
            args.extend(["-b:a", options.audio_bitrate])
        if not options.audio_only and options.video_codec != "copy":
            args.extend(["-pix_fmt", options.pixel_format])
        if options.threads is not None:
            args.extend(["-threads", str(options.threads)])
        if Path(output).suffix.lower() in {".mp4", ".m4v"}:
            args.extend(["-movflags", "+faststart"])
        args.append(output)
        required = _codec_requirements(
            ("video", None if options.audio_only else options.video_codec),
            ("audio", options.audio_codec),
        )
        if options.hardware_acceleration:
            required = (*required, f"hwaccel:{options.hardware_acceleration}")
        streams = ("audio",) if options.audio_only else ("video", "audio")
        operations = (
            (
                "select the first audio stream and drop video"
                if options.audio_only
                else "select the first video and first audio streams when present"
            ),
            "preserve compatible container metadata and chapters",
            f"video codec: {options.video_codec or 'container/FFmpeg default'}",
            f"audio codec: {options.audio_codec or 'container/FFmpeg default'}",
            f"pixel format: {'not applicable' if options.audio_only else options.pixel_format}",
            (
                f"hardware acceleration: {options.hardware_acceleration}; no silent fallback"
                if options.hardware_acceleration
                else "hardware acceleration: none; use the software path"
            ),
        )
        return self._plan(
            "convert",
            args,
            inputs=[source],
            outputs=[output],
            force=force,
            timeout_seconds=timeout_seconds,
            capabilities=required,
            streams=streams,
            operations=operations,
            metadata={"required_stream_types": ["audio"] if options.audio_only else []},
        )

    def resize(
        self,
        input_file: str,
        output_file: str,
        options: ResizeOptions,
        *,
        force: bool = False,
        timeout_seconds: float | None = None,
    ) -> ExecutionPlan:
        source, output = normalized_path(input_file), normalized_path(output_file)
        args = ["-i", source, "-vf", f"scale={options.width}:{options.height}"]
        if options.video_codec:
            args.extend(["-c:v", options.video_codec])
        if options.audio_codec:
            args.extend(["-c:a", options.audio_codec])
        if options.video_codec != "copy":
            args.extend(["-pix_fmt", options.pixel_format])
        if options.threads is not None:
            args.extend(["-threads", str(options.threads)])
        if Path(output).suffix.lower() in {".mp4", ".mov", ".m4v"}:
            args.extend(["-movflags", "+faststart"])
        args.append(output)
        return self._plan(
            "resize",
            args,
            inputs=[source],
            outputs=[output],
            force=force,
            timeout_seconds=timeout_seconds,
            capabilities=(
                "filter:scale",
                *_codec_requirements(("video", options.video_codec), ("audio", options.audio_codec)),
            ),
            streams=("video", "audio"),
            operations=(f"scale video to {options.width}x{options.height}",),
            metadata={"required_stream_types": ["video"]},
        )

    def compress(
        self,
        input_file: str,
        output_file: str,
        options: CompressOptions | None = None,
        *,
        force: bool = False,
        timeout_seconds: float | None = None,
    ) -> ExecutionPlan:
        options = options or CompressOptions()
        source, output = normalized_path(input_file), normalized_path(output_file)
        required = _codec_requirements(("video", options.video_codec), ("audio", options.audio_codec))
        base = ["-i", source, "-c:v", options.video_codec]
        operations: list[str] = []
        steps: tuple[ExecutionStep, ...] = ()
        metadata: dict[str, object] = {"required_stream_types": ["video"]}
        if options.target_size_bytes is not None and options.two_pass:
            if options.video_codec == "copy":
                raise ValidationError("video codec copy cannot satisfy a two-pass target-size contract")
            try:
                duration = FFprobeRunner(self.ffprobe_path).get_duration(source)
            except RuntimeError as exc:
                raise _planning_probe_failure(exc) from exc
            if duration <= 0:
                raise ValidationError("target-size compression requires a positive probed duration")
            audio_bps = parse_bitrate(options.audio_bitrate)
            audio_bytes = audio_bps * duration / 8
            overhead_fraction = options.container_overhead_percent / 100
            available = options.target_size_bytes * (1 - overhead_fraction) - audio_bytes
            minimum_video_bytes = options.minimum_video_bitrate * duration / 8
            minimum_target = int((audio_bytes + minimum_video_bytes) / (1 - overhead_fraction)) + 1
            if available < minimum_video_bytes:
                raise ValidationError(
                    f"target is not feasible at the {options.minimum_video_bitrate} bps quality floor; "
                    f"use at least {_human_bytes(minimum_target)} or shorten/lower the audio bitrate"
                )
            video_bps = int(available * 8 / duration)
            video_bitrate = f"{video_bps}"
            passlog = "<pyffmpegcore-passlog>"
            first: tuple[str, ...] = (
                self.ffmpeg_path,
                "-i",
                source,
                "-c:v",
                options.video_codec,
                "-b:v",
                video_bitrate,
                "-preset",
                options.preset,
                "-pass",
                "1",
                "-passlogfile",
                passlog,
                "-an",
                "-f",
                "null",
                os.devnull,
            )
            second_args = [
                "-i",
                source,
                "-c:v",
                options.video_codec,
                "-b:v",
                video_bitrate,
                "-preset",
                options.preset,
                "-pass",
                "2",
                "-passlogfile",
                passlog,
                "-pix_fmt",
                options.pixel_format,
                "-c:a",
                options.audio_codec,
                "-b:a",
                options.audio_bitrate,
            ]
            if options.threads is not None:
                first = (*first[:-1], "-threads", str(options.threads), first[-1])
                second_args.extend(["-threads", str(options.threads)])
            if Path(output).suffix.lower() in {".mp4", ".mov", ".m4v"}:
                second_args.extend(["-movflags", "+faststart"])
            second_args.append(output)
            second = (self.ffmpeg_path, *second_args)
            steps = (ExecutionStep("analysis-pass", first), ExecutionStep("encode-pass", second))
            args = list(first[1:])
            operations.extend(
                [
                    f"fit output under {options.target_size_bytes} bytes",
                    f"reserve {options.audio_bitrate} audio and {options.container_overhead_percent:g}% container overhead",
                    f"two-pass video bitrate: {video_bps} bps",
                    f"quality floor: {options.minimum_video_bitrate} bps",
                ]
            )
            metadata.update(
                {
                    "estimated_output_bytes": options.target_size_bytes,
                    "target_size_bytes": options.target_size_bytes,
                    "minimum_feasible_bytes": minimum_target,
                    "duration_seconds": duration,
                    "temporary_placeholders": [passlog],
                }
            )
        else:
            args = base
            if options.video_codec != "copy":
                if options.video_bitrate:
                    args.extend(["-b:v", options.video_bitrate])
                    operations.append(f"encode video at {options.video_bitrate}")
                else:
                    args.extend(["-crf", str(options.crf)])
                    operations.append(f"constant quality CRF {options.crf}")
                args.extend(["-preset", options.preset, "-pix_fmt", options.pixel_format])
            args.extend(["-c:a", options.audio_codec, "-b:a", options.audio_bitrate])
            if options.threads is not None:
                args.extend(["-threads", str(options.threads)])
            if Path(output).suffix.lower() in {".mp4", ".mov", ".m4v"}:
                args.extend(["-movflags", "+faststart"])
            args.append(output)
        return self._plan(
            "compress",
            args,
            inputs=[source],
            outputs=[output],
            force=force,
            timeout_seconds=timeout_seconds,
            capabilities=required,
            streams=("video", "audio"),
            operations=tuple(operations),
            metadata=metadata,
            steps=steps,
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
        timeout_seconds: float | None = None,
    ) -> ExecutionPlan:
        source, output = normalized_path(input_file), normalized_path(output_file)
        audio_args, selected_codec = _audio_output_args(output, audio_bitrate, audio_codec)
        args = ["-i", source, "-vn", *audio_args]
        if sample_rate is not None:
            if sample_rate <= 0:
                raise ValidationError("sample rate must be positive")
            args.extend(["-ar", str(sample_rate)])
        if channels is not None:
            if channels <= 0:
                raise ValidationError("channels must be positive")
            args.extend(["-ac", str(channels)])
        if threads is not None:
            if threads <= 0:
                raise ValidationError("threads must be positive")
            args.extend(["-threads", str(threads)])
        args.append(output)
        return self._plan(
            "extract-audio",
            args,
            inputs=[source],
            outputs=[output],
            force=force,
            timeout_seconds=timeout_seconds,
            capabilities=_codec_requirements(
                ("audio", selected_codec),
            ),
            streams=("audio",),
            operations=("drop video streams", f"encode audio with {selected_codec}"),
            metadata={"required_stream_types": ["audio"]},
        )

    def thumbnail(
        self,
        input_file: str,
        output_file: str,
        *,
        timestamp: str = "00:00:01",
        width: int = 320,
        height: int | None = None,
        quality: int = 2,
        force: bool = False,
        timeout_seconds: float | None = None,
    ) -> ExecutionPlan:
        if width <= 0 or (height is not None and height <= 0) or not 1 <= quality <= 31:
            raise ValidationError("thumbnail dimensions must be positive and quality must be between 1 and 31")
        source, output = normalized_path(input_file), normalized_path(output_file)
        scale = f"scale={width}:{height if height is not None else -1}"
        args = [
            "-i",
            source,
            "-ss",
            timestamp,
            "-frames:v",
            "1",
            "-vf",
            scale,
            "-q:v",
            str(quality),
            "-update",
            "1",
            output,
        ]
        return self._plan(
            "thumbnail",
            args,
            inputs=[source],
            outputs=[output],
            force=force,
            timeout_seconds=timeout_seconds,
            streams=("video:0",),
            operations=(f"seek to {timestamp}", f"scale to {width}x{height or 'auto'}", "write one image"),
            metadata={"required_stream_types": ["video"]},
        )

    def waveform(
        self,
        input_file: str,
        output_file: str,
        *,
        width: int = 800,
        height: int = 200,
        colors: str = "white",
        force: bool = False,
        timeout_seconds: float | None = None,
    ) -> ExecutionPlan:
        if width <= 0 or height <= 0:
            raise ValidationError("waveform dimensions must be positive")
        source, output = normalized_path(input_file), normalized_path(output_file)
        args = [
            "-i",
            source,
            "-filter_complex",
            f"[0:a]showwavespic=s={width}x{height}:colors={colors}[waveform]",
            "-map",
            "[waveform]",
            "-frames:v",
            "1",
            "-update",
            "1",
            output,
        ]
        return self._plan(
            "waveform",
            args,
            inputs=[source],
            outputs=[output],
            force=force,
            timeout_seconds=timeout_seconds,
            streams=("audio:0",),
            operations=(f"render audio waveform at {width}x{height} in {colors}",),
            metadata={"required_stream_types": ["audio"]},
        )

    def speed(
        self,
        kind: str,
        input_file: str,
        output_file: str,
        *,
        factor: float,
        preserve_pitch: bool = True,
        force: bool = False,
        timeout_seconds: float | None = None,
    ) -> ExecutionPlan:
        if kind not in {"video", "audio"}:
            raise ValidationError("speed kind must be video or audio")
        if factor <= 0:
            raise ValidationError("speed factor must be positive")
        source, output = normalized_path(input_file), normalized_path(output_file)
        try:
            media = FFprobeRunner(self.ffprobe_path).probe(source)
        except RuntimeError as exc:
            raise _planning_probe_failure(exc) from exc
        has_audio = bool(media.get("audio"))
        sample_rate = media.get("audio", {}).get("sample_rate", 44100)
        audio_filter = (
            _atempo_chain(factor) if preserve_pitch else f"asetrate={sample_rate}*{factor},aresample={sample_rate}"
        )
        capabilities: tuple[str, ...]
        streams: tuple[str, ...]
        if kind == "video":
            args = ["-i", source]
            if has_audio:
                graph = f"[0:v]setpts=(PTS-STARTPTS)/{factor}[v];[0:a]{audio_filter}[a]"
                args.extend(["-filter_complex", graph, "-map", "[v]", "-map", "[a]"])
            else:
                args.extend(["-vf", f"setpts=(PTS-STARTPTS)/{factor}"])
            args.extend(["-c:v", "libx264"])
            if has_audio:
                args.extend(["-c:a", "aac"])
            args.append(output)
            capabilities = ("filter:setpts", "encoder:libx264") + (
                ("filter:atempo", "encoder:aac") if has_audio else ()
            )
            streams = ("video:0", "audio:0" if has_audio else "audio:dropped")
            required_streams = ["video"]
        else:
            audio_args, codec = _audio_output_args(output, "192k")
            args = ["-i", source, "-filter:a", audio_filter, *audio_args, output]
            capabilities = (
                "filter:atempo",
                *_codec_requirements(
                    ("audio", codec),
                ),
            )
            streams = ("audio:0",)
            required_streams = ["audio"]
        return self._plan(
            f"speed/{kind}",
            args,
            inputs=[source],
            outputs=[output],
            force=force,
            timeout_seconds=timeout_seconds,
            capabilities=capabilities,
            streams=streams,
            operations=(f"change playback speed by {factor:g}x", f"preserve pitch: {preserve_pitch}"),
            metadata={"required_stream_types": required_streams},
        )

    def concat(
        self,
        input_files: list[str],
        output_file: str,
        *,
        mode: str = "copy",
        video_codec: str = "libx264",
        audio_codec: str = "aac",
        force: bool = False,
        timeout_seconds: float | None = None,
    ) -> ExecutionPlan:
        if len(input_files) < 2:
            raise ValidationError("concat requires at least two inputs")
        if mode not in {"copy", "reencode"}:
            raise ValidationError("concat mode must be copy or reencode")
        inputs = [normalized_path(value) for value in input_files]
        output = normalized_path(output_file)
        metadata: dict[str, object] = {"required_stream_types": ["video"]}
        capabilities: tuple[str, ...]
        operations: tuple[str, ...]
        if mode == "copy":
            manifest = "<pyffmpegcore-concat-manifest>"
            args = ["-f", "concat", "-safe", "0", "-i", manifest, "-c", "copy", output]
            metadata["concat_manifest"] = inputs
            capabilities = ("demuxer:concat",)
            operations = ("stream-copy matching inputs in the listed order",)
        else:
            args = []
            for value in inputs:
                args.extend(["-i", value])
            video_inputs = "".join(f"[{index}:v]" for index in range(len(inputs)))
            audio_inputs = "".join(f"[{index}:a]" for index in range(len(inputs)))
            graph = (
                f"{video_inputs}concat=n={len(inputs)}:v=1:a=0[vout];{audio_inputs}concat=n={len(inputs)}:v=0:a=1[aout]"
            )
            args.extend(
                [
                    "-filter_complex",
                    graph,
                    "-map",
                    "[vout]",
                    "-map",
                    "[aout]",
                    "-c:v",
                    video_codec,
                    "-c:a",
                    audio_codec,
                    output,
                ]
            )
            capabilities = ("filter:concat", *_codec_requirements(("video", video_codec), ("audio", audio_codec)))
            operations = (
                f"decode and concatenate {len(inputs)} inputs",
                f"encode {video_codec} video and {audio_codec} audio",
            )
            metadata["required_stream_types"] = ["video", "audio"]
        return self._plan(
            f"concat/{mode}",
            args,
            inputs=inputs,
            outputs=[output],
            force=force,
            timeout_seconds=timeout_seconds,
            capabilities=capabilities,
            streams=("video:all", "audio:all"),
            operations=operations,
            metadata=metadata,
        )

    def subtitles(
        self,
        action: str,
        video_file: str,
        output_file: str,
        *,
        subtitle_file: str | None = None,
        language: str = "eng",
        stream_index: int = 0,
        font_size: int = 24,
        font_color: str = "&HFFFFFF",
        force: bool = False,
        timeout_seconds: float | None = None,
    ) -> ExecutionPlan:
        if action not in {"add", "extract", "burn"}:
            raise ValidationError("subtitle action must be add, extract, or burn")
        if action in {"add", "burn"} and subtitle_file is None:
            raise ValidationError("subtitle file is required for add and burn")
        video, output = normalized_path(video_file), normalized_path(output_file)
        subtitle = normalized_path(subtitle_file) if subtitle_file else None
        inputs = [video, *([subtitle] if subtitle else [])]
        capabilities: tuple[str, ...]
        streams: tuple[str, ...]
        operations: tuple[str, ...]
        if action == "add":
            args = [
                "-i",
                video,
                "-i",
                subtitle or "",
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-map",
                "1:0",
                "-c:v",
                "copy",
                "-c:a",
                "copy",
                "-c:s",
                "mov_text",
                "-metadata:s:s:0",
                f"language={language}",
                output,
            ]
            capabilities = ("encoder:mov_text",)
            streams = ("video:0", "audio:all", "subtitle:external")
            operations = (f"add selectable subtitle track labelled {language}", "copy existing video and audio")
            required = []
            metadata: dict[str, object] = {
                "input_stream_requirements": {video: ["video"], subtitle: ["subtitle"]},
            }
        elif action == "extract":
            if stream_index < 0:
                raise ValidationError("subtitle stream index must not be negative")
            args = ["-i", video, "-map", f"0:s:{stream_index}", "-c:s", "srt", output]
            capabilities = ("encoder:srt",)
            streams = (f"subtitle:{stream_index}",)
            operations = (f"extract subtitle stream {stream_index} as SRT",)
            required = ["subtitle"]
            metadata = {}
        else:
            if font_size <= 0:
                raise ValidationError("subtitle font size must be positive")
            source = subtitle or ""
            if "'" in source:
                source = "<pyffmpegcore-subtitle-copy>"
                metadata = {"subtitle_copy_source": subtitle}
            else:
                metadata = {}
            subtitle_filter = (
                f"subtitles=filename='{_escape_filter_path(source)}':"
                f"force_style='FontSize={font_size},PrimaryColour={font_color}'"
            )
            args = ["-i", video, "-vf", subtitle_filter, "-c:a", "copy", output]
            capabilities = ("filter:subtitles",)
            streams = ("video:0", "audio:all", "subtitle:external")
            operations = (f"burn subtitle text at font size {font_size}", "copy audio")
            required = []
            metadata["input_stream_requirements"] = {video: ["video"], subtitle: ["subtitle"]}
        metadata["required_stream_types"] = required
        return self._plan(
            f"subtitles/{action}",
            args,
            inputs=inputs,
            outputs=[output],
            force=force,
            timeout_seconds=timeout_seconds,
            capabilities=capabilities,
            streams=streams,
            operations=operations,
            metadata=metadata,
        )

    def mix_audio(
        self,
        action: str,
        input_files: list[str],
        output_file: str,
        *,
        volumes: list[float] | None = None,
        crossfade_duration: float = 2.0,
        background_volume: float = 0.3,
        force: bool = False,
        timeout_seconds: float | None = None,
    ) -> ExecutionPlan:
        if action not in {"mix", "concat", "mashup", "background"}:
            raise ValidationError("unsupported audio mix action")
        if len(input_files) < 2:
            raise ValidationError("at least two audio inputs are required")
        inputs = [normalized_path(value) for value in input_files]
        output = normalized_path(output_file)
        args: list[str] = []
        for value in inputs:
            args.extend(["-i", value])
        if action == "mix":
            selected_volumes = volumes or [1.0] * len(inputs)
            if len(selected_volumes) != len(inputs) or any(value <= 0 for value in selected_volumes):
                raise ValidationError("volumes must be positive and match the number of inputs")
            parts = [
                f"[{index}:a]{f'volume={volume}' if volume != 1.0 else 'anull'}[a{index}]"
                for index, volume in enumerate(selected_volumes)
            ]
            labels = "".join(f"[a{index}]" for index in range(len(inputs)))
            parts.append(f"{labels}amix=inputs={len(inputs)}:duration=longest:normalize=0[aout]")
            graph, mapped, bitrate, capabilities = ";".join(parts), "[aout]", "192k", ("filter:amix",)
        elif action == "concat":
            labels = "".join(f"[{index}:a]" for index in range(len(inputs)))
            graph, mapped, bitrate, capabilities = (
                f"{labels}concat=n={len(inputs)}:v=0:a=1[aout]",
                "[aout]",
                "192k",
                ("filter:concat",),
            )
        elif action == "mashup":
            if crossfade_duration <= 0:
                raise ValidationError("crossfade duration must be positive")
            parts = []
            current = "[0:a]"
            for index in range(1, len(inputs)):
                target = f"[a{index}]"
                parts.append(f"{current}[{index}:a]acrossfade=d={crossfade_duration}:c1=tri:c2=tri{target}")
                current = target
            graph, mapped, bitrate, capabilities = ";".join(parts), current, "256k", ("filter:acrossfade",)
        else:
            if len(inputs) != 2 or background_volume <= 0:
                raise ValidationError("background mixing requires exactly two inputs and a positive volume")
            graph = (
                f"[1:a]volume={background_volume}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0[aout]"
            )
            mapped, bitrate, capabilities = "[aout]", "192k", ("filter:amix",)
        audio_args, codec = _audio_output_args(output, bitrate)
        args.extend(["-filter_complex", graph, "-map", mapped, *audio_args, output])
        return self._plan(
            f"mix-audio/{action}",
            args,
            inputs=inputs,
            outputs=[output],
            force=force,
            timeout_seconds=timeout_seconds,
            capabilities=(
                *capabilities,
                *_codec_requirements(
                    ("audio", codec),
                ),
            ),
            streams=tuple(f"audio:{index}" for index in range(len(inputs))),
            operations=(f"{action} {len(inputs)} audio inputs", f"encode output with {codec}"),
            metadata={"required_stream_types": ["audio"]},
        )

    def normalize_audio(
        self,
        input_file: str,
        output_file: str,
        *,
        method: str = "loudnorm",
        target_i: float = -16.0,
        target_tp: float = -1.5,
        target_lra: float = 11.0,
        force: bool = False,
        timeout_seconds: float | None = None,
    ) -> ExecutionPlan:
        source, output = normalized_path(input_file), normalized_path(output_file)
        if method == "loudnorm":
            graph = f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}"
            bitrate = "192k"
            operations = (f"normalize to I={target_i} LUFS, TP={target_tp} dBTP, LRA={target_lra} LU",)
        elif method == "master":
            graph = (
                "loudnorm=I=-16:TP=-1.5:LRA=11,"
                "compand=attacks=0.0001:decays=0.2:points=-70/-70|-60/-20|-20/-20|20/20,"
                "alimiter=limit=-1dB:level=disabled"
            )
            bitrate = "256k"
            operations = ("normalize, compress dynamics, and apply a -1 dB limiter",)
        else:
            raise ValidationError("normalization method must be loudnorm or master")
        audio_args, codec = _audio_output_args(output, bitrate)
        args = ["-i", source, "-af", graph, *audio_args, output]
        capabilities = [
            "filter:loudnorm",
            *_codec_requirements(
                ("audio", codec),
            ),
        ]
        if method == "master":
            capabilities.extend(("filter:compand", "filter:alimiter"))
        return self._plan(
            "normalize-audio",
            args,
            inputs=[source],
            outputs=[output],
            force=force,
            timeout_seconds=timeout_seconds,
            capabilities=tuple(capabilities),
            streams=("audio:0",),
            operations=operations,
            metadata={"required_stream_types": ["audio"]},
        )

    def images(
        self,
        action: str,
        input_dir: str,
        output_dir: str,
        *,
        output_format: str = "jpg",
        quality: int = 85,
        resize: tuple[int, int] | None = None,
        max_width: int = 1920,
        max_height: int = 1080,
        force: bool = False,
        timeout_seconds: float | None = None,
    ) -> ExecutionPlan:
        if action not in {"convert", "optimize", "webp"}:
            raise ValidationError("unsupported image workflow")
        if not 1 <= quality <= 100:
            raise ValidationError("image quality must be between 1 and 100")
        source_dir, target_dir = Path(normalized_path(input_dir)), Path(normalized_path(output_dir))
        patterns = ("*.png", "*.jpg", "*.jpeg", "*.tiff", "*.bmp", "*.gif")
        inputs = sorted({path for pattern in patterns for path in source_dir.glob(pattern)})
        if not inputs:
            raise ValidationError(f"no supported images found in {source_dir}")
        extension = "webp" if action == "webp" else "jpg" if action == "optimize" else output_format.lstrip(".")
        steps = []
        outputs = []
        planning_warnings: list[str] = []
        for index, source in enumerate(inputs):
            output = target_dir / f"{source.stem}.{extension}"
            outputs.append(str(output))
            image_resize = resize
            if action == "optimize":
                try:
                    media = FFprobeRunner(self.ffprobe_path).probe(str(source))
                except RuntimeError:
                    planning_warnings.append(f"probe deferred for unreadable image: {source}")
                else:
                    video = media.get("video", {})
                    width, height = video.get("width", 0), video.get("height", 0)
                    if width and height and (width > max_width or height > max_height):
                        ratio = min(max_width / width, max_height / height)
                        image_resize = (int(width * ratio), int(height * ratio))
            args = ["-i", str(source)]
            if image_resize:
                if image_resize[0] <= 0 or image_resize[1] <= 0:
                    raise ValidationError("image resize dimensions must be positive")
                args.extend(["-vf", f"scale={image_resize[0]}:{image_resize[1]}"])
            suffix = output.suffix.lower()
            if suffix in {".jpg", ".jpeg"}:
                args.extend(["-q:v", str(min(31, max(1, 31 - int(quality * 31 / 100))))])
            elif suffix == ".webp":
                args.extend(["-quality", str(quality)])
            elif suffix == ".png":
                args.extend(["-compression_level", str(min(9, max(0, 9 - int(quality * 9 / 100))))])
            args.extend(["-frames:v", "1"])
            if suffix in {".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
                args.extend(["-update", "1"])
            args.append(str(output))
            steps.append(ExecutionStep(f"image-{index + 1}", (self.ffmpeg_path, *args)))
        command = list(steps[0].command[1:])
        capabilities = ("encoder:libwebp", "muxer:webp") if action == "webp" else ("muxer:image2",)
        if action == "optimize" or resize:
            capabilities = (*capabilities, "filter:scale")
        return self._plan(
            f"images/{action}",
            command,
            inputs=[str(path) for path in inputs],
            outputs=outputs,
            force=force,
            timeout_seconds=timeout_seconds,
            capabilities=capabilities,
            streams=("video:image",),
            operations=(f"{action} {len(inputs)} images as {extension}", f"quality: {quality}"),
            warnings=tuple(planning_warnings),
            metadata={
                "required_stream_types": ["video"],
                "item_count": len(inputs),
                "output_directory": str(target_dir),
            },
            steps=tuple(steps),
        )

    def image(
        self,
        input_file: str,
        output_file: str,
        *,
        quality: int = 85,
        resize: tuple[int, int] | None = None,
        force: bool = False,
        timeout_seconds: float | None = None,
    ) -> ExecutionPlan:
        """Plan one still-image conversion without routing through a directory batch."""
        if not 1 <= quality <= 100:
            raise ValidationError("image quality must be between 1 and 100")
        source, output = normalized_path(input_file), normalized_path(output_file)
        args = ["-i", source]
        capabilities: tuple[str, ...] = ()
        if resize is not None:
            if resize[0] <= 0 or resize[1] <= 0:
                raise ValidationError("image resize dimensions must be positive")
            args.extend(["-vf", f"scale={resize[0]}:{resize[1]}"])
            capabilities = ("filter:scale",)
        suffix = Path(output).suffix.lower()
        if suffix in {".jpg", ".jpeg"}:
            args.extend(["-q:v", str(min(31, max(1, 31 - int(quality * 31 / 100))))])
            capabilities = (*capabilities, "muxer:image2")
        elif suffix == ".webp":
            args.extend(["-quality", str(quality)])
            capabilities = (*capabilities, "encoder:libwebp", "muxer:webp")
        elif suffix == ".png":
            args.extend(["-compression_level", str(min(9, max(0, 9 - int(quality * 9 / 100))))])
            capabilities = (*capabilities, "muxer:image2")
        else:
            capabilities = (*capabilities, "muxer:image2")
        args.extend(["-frames:v", "1"])
        if suffix in {".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
            args.extend(["-update", "1"])
        args.append(output)
        return self._plan(
            "image/convert",
            args,
            inputs=[source],
            outputs=[output],
            force=force,
            timeout_seconds=timeout_seconds,
            capabilities=capabilities,
            streams=("video:image",),
            operations=(f"convert one image to {suffix or 'the requested format'}", f"quality: {quality}"),
            metadata={"required_stream_types": ["video"]},
        )
