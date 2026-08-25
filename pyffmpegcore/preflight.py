"""Non-mutating workflow preflight with versioned human/JSON facts."""

from __future__ import annotations

import os
import platform
import shutil
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .capabilities import CapabilityInventory, requirements_for
from .domain import ExecutionPlan, OverwritePolicy
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
        return {
            "schema_version": self.schema_version,
            "workflow": self.workflow,
            "ok": self.ok,
            "checks": [asdict(check) for check in self.checks],
        }

    def render(self) -> str:
        lines = [f"Preflight {'PASS' if self.ok else 'FAIL'} — {self.workflow}"]
        symbols = {"pass": "OK", "warn": "WARN", "fail": "FAIL"}
        for check in self.checks:
            lines.append(f"[{symbols[check.status]}] {check.name}: {check.message}")
            if check.hint:
                lines.append(f"  Remedy: {check.hint}")
        return "\n".join(lines)


def _nearest_existing_parent(path: Path) -> Path:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


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

        inventory = self._inventory or CapabilityInventory.inspect(self.ffmpeg_path)
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
        probe = FFprobeRunner(self.ffprobe_path)
        for value in plan.inputs:
            parsed = urlsplit(value)
            if parsed.scheme and parsed.scheme != "file":
                requirement = f"input-protocol:{parsed.scheme}"
                if inventory.supports(requirement):
                    checks.append(PreflightCheck(f"input/{value}", "pass", f"Protocol {parsed.scheme} is available"))
                else:
                    checks.append(
                        PreflightCheck(
                            f"input/{value}",
                            "fail",
                            f"Missing input protocol: {parsed.scheme}",
                            capability_remedy(requirement, inventory),
                        )
                    )
                continue
            path = Path(parsed.path if parsed.scheme == "file" else value)
            if not path.is_file() or not os.access(path, os.R_OK):
                checks.append(PreflightCheck(f"input/{value}", "fail", "Input is missing or unreadable"))
                continue
            checks.append(PreflightCheck(f"input/{value}", "pass", "Input is readable"))
            if required_stream_types:
                try:
                    media = probe.probe_media(str(path))
                except RuntimeError as exc:
                    checks.append(PreflightCheck(f"probe/{value}", "fail", f"Input probe failed: {exc}"))
                    continue
                available = {stream.codec_type for stream in media.streams}
                missing_streams = [kind for kind in required_stream_types if kind not in available]
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
                            f"Required streams available: {', '.join(required_stream_types)}",
                        )
                    )

        estimated_bytes = int(plan.metadata.get("estimated_output_bytes") or 0)
        if estimated_bytes <= 0:
            estimated_bytes = sum(Path(value).stat().st_size for value in plan.inputs if Path(value).is_file())
        for value in plan.outputs:
            output = Path(value)
            parent = _nearest_existing_parent(output.parent)
            if not parent.is_dir() or not os.access(parent, os.W_OK):
                checks.append(PreflightCheck(f"output/{value}", "fail", f"Output parent is not writable: {parent}"))
                continue
            checks.append(PreflightCheck(f"output/{value}", "pass", f"Output parent is writable: {parent}"))
            if output.exists() and plan.policy.overwrite is OverwritePolicy.REFUSE:
                checks.append(
                    PreflightCheck(
                        f"collision/{value}",
                        "fail",
                        "Output already exists and overwrite policy is refuse",
                        "Choose another output or explicitly use overwrite policy replace.",
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
