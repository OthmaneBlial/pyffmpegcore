"""Non-mutating workflow preflight with versioned human/JSON facts."""

from __future__ import annotations

import os
import platform
import re
import shutil
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ._terminal import terminal_safe_text
from .capabilities import CapabilityInventory, requirements_for
from .domain import ExecutionPlan, MediaInfo, OverwritePolicy, is_url_like_path
from .probe import FFprobeRunner

PREFLIGHT_SCHEMA_VERSION = "1.0"
_CONTAINER_BY_SUFFIX = {
    ".aac": "adts",
    ".avi": "avi",
    ".flac": "flac",
    ".gif": "gif",
    ".jpg": "image2",
    ".jpeg": "image2",
    ".m4a": "ipod",
    ".mkv": "matroska",
    ".mov": "mov",
    ".mp3": "mp3",
    ".mp4": "mp4",
    ".ogg": "ogg",
    ".opus": "opus",
    ".png": "image2",
    ".srt": "srt",
    ".wav": "wav",
    ".webm": "webm",
    ".webp": "webp",
}


@dataclass(frozen=True, slots=True)
class PreflightCheck:
    """One deterministic preflight fact."""

    name: str
    status: str
    message: str
    hint: str | None = None


@dataclass(frozen=True, slots=True)
class PreflightReport:
    """Versioned preflight result shared by human and JSON presenters."""

    workflow: str
    checks: tuple[PreflightCheck, ...]
    schema_version: str = PREFLIGHT_SCHEMA_VERSION

    @property
    def ok(self) -> bool:
        return all(check.status != "fail" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        """Return versioned JSON-ready preflight facts and overall status."""
        return {
            "schema_version": self.schema_version,
            "workflow": self.workflow,
            "ok": self.ok,
            "checks": [asdict(check) for check in self.checks],
        }

    def render(self) -> str:
        """Render checks and available remedies as a concise human-readable report."""
        lines = [f"Preflight {'PASS' if self.ok else 'FAIL'} — {terminal_safe_text(self.workflow)}"]
        symbols = {"pass": "OK", "warn": "WARN", "fail": "FAIL"}
        for check in self.checks:
            lines.append(
                f"[{symbols[check.status]}] {terminal_safe_text(check.name)}: {terminal_safe_text(check.message)}"
            )
            if check.hint:
                lines.append(f"  Remedy: {terminal_safe_text(check.hint)}")
        return "\n".join(lines)


def _nearest_existing_parent(path: Path) -> Path:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def _input_scheme(value: str) -> str | None:
    """Return a remote URI scheme without misclassifying Windows drive paths."""
    if re.match(r"^[A-Za-z]:[\\/]", value):
        return None
    scheme = urlsplit(value).scheme
    return scheme if scheme and scheme != "file" else None


def _concat_copy_stream_signature(media: MediaInfo) -> tuple[tuple[object, ...], ...]:
    """Return stream facts that the concat demuxer expects to match."""
    detail_fields = ("codec_tag_string", "codec_time_base", "time_base", "pix_fmt", "field_order")
    return tuple(
        (
            stream.codec_type,
            stream.codec_name,
            stream.profile,
            stream.width,
            stream.height,
            stream.sample_rate,
            stream.channels,
            tuple((name, stream.details.get(name)) for name in detail_fields),
        )
        for stream in media.streams
    )


def capability_remedy(requirement: str, inventory: CapabilityInventory) -> str:
    """Return a concrete fallback or platform-specific installation remedy."""
    fallbacks = {
        "encoder:libx264": "encoder:mpeg4",
        "encoder:libopus": "encoder:aac",
        "encoder:libwebp": "encoder:mjpeg",
        "filter:subtitles": "encoder:mov_text",
    }
    fallback = fallbacks.get(requirement)
    if fallback and inventory.supports(fallback):
        return f"Use the tested fallback {fallback}, or install an FFmpeg build providing {requirement}."
    system = platform.system()
    commands = {
        "Darwin": "Install a fuller build with `brew install ffmpeg` and verify it with `pyffmpegcore doctor`.",
        "Windows": "Install a full build with `winget install Gyan.FFmpeg` and verify it with `pyffmpegcore doctor`.",
        "Linux": "Install your distribution's full FFmpeg package and verify it with `pyffmpegcore doctor`.",
    }
    return commands.get(system, f"Install an FFmpeg build providing {requirement} and run `pyffmpegcore doctor`.")


class PreflightEngine:
    """Check a plan without creating directories, outputs, or temporary files."""

    def __init__(
        self,
        *,
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
        inventory: CapabilityInventory | None = None,
        executable_resolver: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self._inventory = inventory
        self._executable_resolver = executable_resolver

    def check(self, plan: ExecutionPlan) -> PreflightReport:
        """Check tools, capabilities, inputs, and output paths without executing.

        Input streams may be probed when the plan requires them. The report
        records failures and remediation hints instead of raising for them.
        """
        checks: list[PreflightCheck] = []
        explicit_binary = any(separator in self.ffmpeg_path for separator in ("/", "\\"))
        resolved = (
            str(Path(self.ffmpeg_path).resolve())
            if explicit_binary and Path(self.ffmpeg_path).is_file()
            else self._executable_resolver(self.ffmpeg_path)
        )
        if resolved is None:
            checks.append(
                PreflightCheck(
                    "ffmpeg",
                    "fail",
                    f"Executable not found: {self.ffmpeg_path}",
                    "Install FFmpeg or pass --ffmpeg-path to a verified executable.",
                )
            )
            return PreflightReport(plan.workflow, tuple(checks))
        checks.append(PreflightCheck("ffmpeg", "pass", f"Executable: {resolved}"))

        try:
            inventory = self._inventory or CapabilityInventory.inspect(self.ffmpeg_path)
        except RuntimeError as exc:
            checks.append(
                PreflightCheck(
                    "capabilities",
                    "fail",
                    f"FFmpeg capability inspection failed: {exc}",
                    "Check that FFmpeg responds to capability listing commands, then rerun preflight.",
                )
            )
            return PreflightReport(plan.workflow, tuple(checks))
        self._inventory = inventory
        requirements = requirements_for(plan.workflow, plan.required_capabilities)
        for requirement in requirements:
            if inventory.supports(requirement):
                checks.append(PreflightCheck(f"capability/{requirement}", "pass", "Available"))
            else:
                checks.append(
                    PreflightCheck(
                        f"capability/{requirement}",
                        "fail",
                        f"Missing required capability: {requirement}",
                        capability_remedy(requirement, inventory),
                    )
                )

        required_stream_types = tuple(plan.metadata.get("required_stream_types", ()))
        input_stream_requirements = plan.metadata.get("input_stream_requirements", {})
        if not isinstance(input_stream_requirements, dict):
            input_stream_requirements = {}
        probe = FFprobeRunner(self.ffprobe_path)
        concat_copy_signatures: list[tuple[tuple[object, ...], ...] | None] = []
        concat_copy_has_remote_input = False
        concat_reencode_dimensions: list[tuple[int, int] | None] = []
        concat_reencode_has_remote_input = False
        for value in plan.inputs:
            remote_scheme = _input_scheme(value)
            parsed = urlsplit(value)
            if remote_scheme:
                if plan.workflow == "concat/copy":
                    concat_copy_signatures.append(None)
                    concat_copy_has_remote_input = True
                elif plan.workflow == "concat/reencode":
                    concat_reencode_dimensions.append(None)
                    concat_reencode_has_remote_input = True
                requirement = f"input-protocol:{remote_scheme}"
                safe_name = f"input/{remote_scheme}://<redacted>"
                if inventory.supports(requirement):
                    checks.append(PreflightCheck(safe_name, "pass", f"Protocol {remote_scheme} is available"))
                else:
                    checks.append(
                        PreflightCheck(
                            safe_name,
                            "fail",
                            f"Missing input protocol: {remote_scheme}",
                            capability_remedy(requirement, inventory),
                        )
                    )
                continue
            path = Path(parsed.path if parsed.scheme == "file" else value)
            if not path.is_file() or not os.access(path, os.R_OK):
                if plan.workflow == "concat/copy":
                    concat_copy_signatures.append(None)
                elif plan.workflow == "concat/reencode":
                    concat_reencode_dimensions.append(None)
                checks.append(PreflightCheck(f"input/{value}", "fail", "Input is missing or unreadable"))
                continue
            checks.append(PreflightCheck(f"input/{value}", "pass", "Input is readable"))
            per_input_streams = input_stream_requirements.get(value, required_stream_types)
            if per_input_streams:
                try:
                    media = probe.probe_media(str(path))
                except RuntimeError as exc:
                    if plan.workflow == "concat/copy":
                        concat_copy_signatures.append(None)
                    elif plan.workflow == "concat/reencode":
                        concat_reencode_dimensions.append(None)
                    checks.append(PreflightCheck(f"probe/{value}", "fail", f"Input probe failed: {exc}"))
                    continue
                if plan.workflow == "concat/copy":
                    concat_copy_signatures.append(_concat_copy_stream_signature(media))
                elif plan.workflow == "concat/reencode":
                    video = next((stream for stream in media.streams if stream.codec_type == "video"), None)
                    dimensions = (video.width, video.height) if video and video.width and video.height else None
                    concat_reencode_dimensions.append(dimensions)
                available = {stream.codec_type for stream in media.streams}
                missing_streams = [kind for kind in per_input_streams if kind not in available]
                if missing_streams:
                    checks.append(
                        PreflightCheck(
                            f"streams/{value}",
                            "fail",
                            f"Missing required streams: {', '.join(missing_streams)}",
                        )
                    )
                else:
                    checks.append(
                        PreflightCheck(
                            f"streams/{value}",
                            "pass",
                            f"Required streams available: {', '.join(per_input_streams)}",
                        )
                    )

        if plan.workflow == "concat/copy":
            known_signatures = [signature for signature in concat_copy_signatures if signature is not None]
            if len(known_signatures) > 1 and any(
                signature != known_signatures[0] for signature in known_signatures[1:]
            ):
                checks.append(
                    PreflightCheck(
                        "concat/copy-compatibility",
                        "fail",
                        "Stream metadata differs between inputs; the concat demuxer expects matching stream layouts.",
                        "Use --mode reencode when stream types match, or normalize the clips to matching stream properties first.",
                    )
                )
            elif concat_copy_has_remote_input:
                checks.append(
                    PreflightCheck(
                        "concat/copy-compatibility",
                        "warn",
                        "Remote input stream metadata cannot be compared during preflight.",
                        "Use local inputs to verify stream metadata before stream-copy concatenation.",
                    )
                )
            elif len(concat_copy_signatures) == len(plan.inputs) and known_signatures:
                checks.append(
                    PreflightCheck(
                        "concat/copy-compatibility",
                        "pass",
                        "Stream metadata matches across inputs; packet-level compatibility is not guaranteed.",
                    )
                )
        elif plan.workflow == "concat/reencode":
            known_dimensions = [dimensions for dimensions in concat_reencode_dimensions if dimensions is not None]
            if len(known_dimensions) > 1 and any(
                dimensions != known_dimensions[0] for dimensions in known_dimensions[1:]
            ):
                checks.append(
                    PreflightCheck(
                        "concat/reencode-compatibility",
                        "fail",
                        "Selected video stream dimensions differ between inputs; the concat filter requires matching resolutions.",
                        "Resize each clip to the same width and height before re-encoding them together.",
                    )
                )
            elif concat_reencode_has_remote_input:
                checks.append(
                    PreflightCheck(
                        "concat/reencode-compatibility",
                        "warn",
                        "Remote input dimensions cannot be compared during preflight.",
                        "Verify every input has matching video dimensions and the required video and audio streams.",
                    )
                )
            elif len(concat_reencode_dimensions) == len(plan.inputs) and len(known_dimensions) == len(plan.inputs):
                checks.append(
                    PreflightCheck(
                        "concat/reencode-compatibility",
                        "pass",
                        "Selected video stream dimensions match across inputs.",
                    )
                )

        estimated_bytes = int(plan.metadata.get("estimated_output_bytes") or 0)
        if estimated_bytes <= 0:
            estimated_bytes = sum(Path(value).stat().st_size for value in plan.inputs if Path(value).is_file())
        for value in plan.outputs:
            if is_url_like_path(value):
                checks.append(
                    PreflightCheck(
                        "output/remote",
                        "fail",
                        "Remote output URLs are not supported by this workflow.",
                        "Choose a local output path, then upload the verified file separately.",
                    )
                )
                continue
            output = Path(value)
            parent = _nearest_existing_parent(output.parent)
            if not parent.is_dir() or not os.access(parent, os.W_OK):
                checks.append(
                    PreflightCheck(
                        f"output/{value}",
                        "fail",
                        f"Output parent is not writable: {parent}",
                        "Choose an output in a writable directory or grant write access to its parent.",
                    )
                )
                continue
            checks.append(PreflightCheck(f"output/{value}", "pass", f"Output parent is writable: {parent}"))
            if output.exists() and plan.policy.overwrite is OverwritePolicy.REFUSE:
                checks.append(
                    PreflightCheck(
                        f"collision/{value}",
                        "fail",
                        "Output already exists and overwrite policy is refuse",
                        "Choose another output or explicitly allow replacement (CLI: --force).",
                    )
                )
            else:
                checks.append(PreflightCheck(f"collision/{value}", "pass", "No blocking output collision"))
            free = shutil.disk_usage(parent).free
            if estimated_bytes and free < estimated_bytes:
                checks.append(
                    PreflightCheck(
                        f"disk/{value}",
                        "fail",
                        f"Insufficient free space: need about {estimated_bytes} bytes, have {free}",
                    )
                )
            else:
                checks.append(
                    PreflightCheck(
                        f"disk/{value}",
                        "pass",
                        f"Free space {free} bytes; estimate {estimated_bytes or 'unknown'}",
                    )
                )

            expected_muxer = _CONTAINER_BY_SUFFIX.get(output.suffix.lower())
            if expected_muxer:
                requirement = f"muxer:{expected_muxer}"
                if inventory.supports(requirement):
                    checks.append(PreflightCheck(f"container/{value}", "pass", f"Muxer available: {expected_muxer}"))
                else:
                    checks.append(
                        PreflightCheck(
                            f"container/{value}",
                            "fail",
                            f"Output extension requires unavailable muxer: {expected_muxer}",
                            capability_remedy(requirement, inventory),
                        )
                    )

        return PreflightReport(plan.workflow, tuple(checks))
