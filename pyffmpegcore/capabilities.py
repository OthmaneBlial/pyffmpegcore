"""FFmpeg capability inventory and workflow requirement catalog."""

from __future__ import annotations

import re
import subprocess
from dataclasses import asdict, dataclass
from typing import Any

CAPABILITY_SCHEMA_VERSION = "1.0"

CORE_ENCODERS = ("aac", "flac", "libmp3lame", "libopus", "libvpx-vp9", "libx264", "mpeg4", "pcm_s16le")
CORE_DECODERS = ("aac", "flac", "h264", "hevc", "mp3", "pcm_s16le", "vp9")
CORE_FILTERS = ("acrossfade", "amix", "atempo", "drawtext", "loudnorm", "scale", "showwavespic", "subtitles")
CORE_MUXERS = ("image2", "matroska", "mp3", "mp4", "ogg", "wav", "webm")
CORE_PROTOCOLS = ("file", "http", "https", "pipe")

WORKFLOW_CAPABILITY_RULES: dict[str, tuple[str, ...]] = {
    "convert": (),
    "compress": (),
    "extract-audio": (),
    "thumbnail": ("filter:scale", "muxer:image2"),
    "waveform": ("filter:showwavespic", "muxer:image2"),
    "speed/video": ("filter:setpts", "encoder:libx264"),
    "speed/audio": ("filter:atempo",),
    "concat/copy": ("demuxer:concat",),
    "concat/reencode": ("filter:concat",),
    "subtitles/add": ("encoder:mov_text",),
    "subtitles/extract": ("encoder:srt",),
    "subtitles/burn": ("filter:subtitles",),
    "mix-audio/mix": ("filter:amix",),
    "mix-audio/concat": ("filter:concat",),
    "mix-audio/mashup": ("filter:acrossfade",),
    "mix-audio/background": ("filter:amix",),
    "normalize-audio": ("filter:loudnorm",),
    "images/convert": ("muxer:image2",),
    "images/optimize": ("filter:scale", "muxer:image2"),
    "images/webp": ("encoder:libwebp", "muxer:webp"),
}


def _listing(binary: str, option: str) -> str:
    try:
        result = subprocess.run(
            [binary, "-hide_banner", option],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    return result.stdout if result.returncode == 0 else ""


def _parse_table(text: str, flag_width: int) -> tuple[str, ...]:
    pattern = re.compile(rf"^\s*[A-Z. ]{{{flag_width}}}\s+(\S+)")
    names: set[str] = set()
    for line in text.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        names.update(part for part in match.group(1).split(",") if part and part != "=")
    return tuple(sorted(names))


def _parse_protocols(text: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    current: set[str] | None = None
    inputs: set[str] = set()
    outputs: set[str] = set()
    for line in text.splitlines():
        value = line.strip()
        if value == "Input:":
            current = inputs
        elif value == "Output:":
            current = outputs
        elif current is not None and value and " " not in value:
            current.add(value)
    return tuple(sorted(inputs)), tuple(sorted(outputs))


@dataclass(frozen=True, slots=True)
class CapabilityInventory:
    """Versioned inventory of an installed FFmpeg executable."""

    binary: str
    encoders: tuple[str, ...]
    decoders: tuple[str, ...]
    filters: tuple[str, ...]
    muxers: tuple[str, ...]
    demuxers: tuple[str, ...]
    input_protocols: tuple[str, ...]
    output_protocols: tuple[str, ...]
    hardware_accelerators: tuple[str, ...]
    schema_version: str = CAPABILITY_SCHEMA_VERSION

    @classmethod
    def inspect(cls, binary: str = "ffmpeg") -> CapabilityInventory:
        protocols = _parse_protocols(_listing(binary, "-protocols"))
        hardware = tuple(
            sorted(
                line.strip()
                for line in _listing(binary, "-hwaccels").splitlines()
                if line.strip() and not line.startswith("Hardware acceleration methods:")
            )
        )
        return cls(
            binary=binary,
            encoders=_parse_table(_listing(binary, "-encoders"), 6),
            decoders=_parse_table(_listing(binary, "-decoders"), 6),
            filters=_parse_table(_listing(binary, "-filters"), 3),
            muxers=_parse_table(_listing(binary, "-muxers"), 3),
            demuxers=_parse_table(_listing(binary, "-demuxers"), 3),
            input_protocols=protocols[0],
            output_protocols=protocols[1],
            hardware_accelerators=hardware,
        )

    def supports(self, requirement: str) -> bool:
        """Check a normalized `kind:name` requirement."""
        try:
            kind, name = requirement.split(":", 1)
        except ValueError:
            return False
        collections = {
            "encoder": self.encoders,
            "decoder": self.decoders,
            "filter": self.filters,
            "muxer": self.muxers,
            "demuxer": self.demuxers,
            "input-protocol": self.input_protocols,
            "output-protocol": self.output_protocols,
            "hwaccel": self.hardware_accelerators,
        }
        return name in collections.get(kind, ())

    def missing(self, requirements: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(requirement for requirement in requirements if not self.supports(requirement))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.update(
            {
                "encoder_count": len(self.encoders),
                "decoder_count": len(self.decoders),
                "filter_count": len(self.filters),
                "muxer_count": len(self.muxers),
                "demuxer_count": len(self.demuxers),
                "core_encoders": {name: name in self.encoders for name in CORE_ENCODERS},
                "core_decoders": {name: name in self.decoders for name in CORE_DECODERS},
                "core_filters": {name: name in self.filters for name in CORE_FILTERS},
                "core_muxers": {name: name in self.muxers for name in CORE_MUXERS},
                "core_protocols": {
                    name: name in self.input_protocols or name in self.output_protocols for name in CORE_PROTOCOLS
                },
                "subtitle_support": {
                    "text_encoders": [name for name in ("ass", "mov_text", "srt", "webvtt") if name in self.encoders],
                    "burn_filter": "subtitles" in self.filters,
                },
            }
        )
        return data


def requirements_for(workflow: str, extra: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Return de-duplicated required capabilities for a workflow plan."""
    return tuple(dict.fromkeys((*WORKFLOW_CAPABILITY_RULES.get(workflow, ()), *extra)))
