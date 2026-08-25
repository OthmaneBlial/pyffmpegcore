"""Translate parsed CLI options into shared typed workflow plans."""

from __future__ import annotations

import argparse
from typing import TypedDict

from .domain import CompressOptions, ConvertOptions
from .errors import ValidationError
from .planning import WorkflowPlanner, parse_bitrate, parse_size


def _planner(args: argparse.Namespace) -> WorkflowPlanner:
    return WorkflowPlanner(ffmpeg_path=args.ffmpeg_path, ffprobe_path=args.ffprobe_path)


class SharedPlanOptions(TypedDict):
    force: bool
    timeout_seconds: float | None


def _shared(args: argparse.Namespace) -> SharedPlanOptions:
    return {
        "force": bool(args.force),
        "timeout_seconds": getattr(args, "timeout", None),
    }


def build_cli_plan(args: argparse.Namespace):
    """Build a plan for every CLI command that may write media output."""
    planner = _planner(args)
    shared = _shared(args)
    command = args.command
    if command == "convert":
        convert_options = ConvertOptions(
            video_codec=args.video_codec,
            audio_codec=args.audio_codec,
            video_bitrate=args.video_bitrate,
            audio_bitrate=args.audio_bitrate,
            pixel_format=args.pix_fmt or "yuv420p",
            threads=args.threads,
            audio_only=args.audio_only,
            hardware_acceleration=args.hwaccel,
        )
        return planner.convert(args.input, args.output, convert_options, **shared)
    if command == "compress":
        target_bytes = None
        if getattr(args, "target_size", None):
            target_bytes = parse_size(args.target_size)
        elif args.target_size_kb is not None:
            target_bytes = args.target_size_kb * 1024
        minimum_bitrate = parse_bitrate(getattr(args, "min_video_bitrate", "100k"))
        compress_options = CompressOptions(
            target_size_bytes=target_bytes,
            crf=args.crf,
            two_pass=args.two_pass,
            video_codec=args.video_codec or "libx264",
            audio_codec=args.audio_codec or "aac",
            video_bitrate=args.video_bitrate,
            audio_bitrate=args.audio_bitrate or "128k",
            preset=args.preset or "medium",
            threads=args.threads,
            container_overhead_percent=getattr(args, "container_overhead_percent", 1.0),
            minimum_video_bitrate=minimum_bitrate,
        )
        return planner.compress(args.input, args.output, compress_options, **shared)
    if command == "extract-audio":
        return planner.extract_audio(
            args.input,
            args.output,
            audio_codec=args.audio_codec,
            audio_bitrate=args.audio_bitrate or "192k",
            sample_rate=args.sample_rate,
            channels=args.channels,
            threads=args.threads,
            **shared,
        )
    if command == "thumbnail":
        return planner.thumbnail(
            args.input,
            args.output,
            timestamp=args.timestamp,
            width=args.width,
            height=args.height,
            quality=args.quality,
            **shared,
        )
    if command == "waveform":
        return planner.waveform(
            args.input,
            args.output,
            width=args.width,
            height=args.height,
            colors=args.colors,
            **shared,
        )
    if command == "speed":
        return planner.speed(
            args.speed_command,
            args.input,
            args.output,
            factor=args.factor,
            preserve_pitch=not args.no_pitch_preserve,
            **shared,
        )
    if command == "concat":
        return planner.concat(
            args.inputs,
            args.output,
            mode=args.mode,
            video_codec=args.video_codec,
            audio_codec=args.audio_codec,
            **shared,
        )
    if command == "subtitles":
        return planner.subtitles(
            args.subtitles_command,
            args.video,
            args.output,
            subtitle_file=getattr(args, "subtitle", None),
            language=getattr(args, "language", "eng"),
            stream_index=getattr(args, "stream_index", 0),
            font_size=getattr(args, "font_size", 24),
            font_color=getattr(args, "font_color", "&HFFFFFF"),
            **shared,
        )
    if command == "mix-audio":
        if args.mix_audio_command == "background":
            inputs = [args.main_input, args.background_input]
        else:
            inputs = args.inputs
        return planner.mix_audio(
            args.mix_audio_command,
            inputs,
            args.output,
            volumes=getattr(args, "volumes", None),
            crossfade_duration=getattr(args, "crossfade_duration", 2.0),
            background_volume=getattr(args, "bg_volume", 0.3),
            **shared,
        )
    if command == "normalize-audio":
        return planner.normalize_audio(
            args.input,
            args.output,
            method=args.method,
            target_i=args.target_i,
            target_tp=args.target_tp,
            target_lra=args.target_lra,
            **shared,
        )
    if command == "images":
        return planner.images(
            args.images_command,
            args.input_dir,
            args.output_dir,
            output_format=getattr(args, "format", "jpg"),
            quality=args.quality,
            resize=tuple(args.resize) if getattr(args, "resize", None) else None,
            max_width=getattr(args, "max_width", 1920),
            max_height=getattr(args, "max_height", 1080),
            **shared,
        )
    raise ValidationError(f"--dry-run and --explain are not supported for the non-writing command {command!r}")
