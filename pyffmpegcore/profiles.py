"""Versioned workflow profile registry with strict JSON/TOML validation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .errors import ValidationError

PROFILE_SCHEMA_VERSION = "1.0"
_PROFILE_FIELDS = {
    "schema_version",
    "name",
    "profile_version",
    "description",
    "workflow",
    "options",
    "required_capabilities",
}


def _is_json_value(value: object) -> bool:
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())
    return False


@dataclass(frozen=True, slots=True)
class Profile:
    """A named, versioned set of choices for one supported workflow."""

    name: str
    profile_version: int
    description: str
    workflow: str
    options: dict[str, Any] = field(default_factory=dict)
    required_capabilities: tuple[str, ...] = ()
    schema_version: str = PROFILE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PROFILE_SCHEMA_VERSION:
            raise ValidationError(
                f"Unsupported profile schema_version {self.schema_version!r}; expected {PROFILE_SCHEMA_VERSION!r}"
            )
        if not self.name or "/" not in self.name:
            raise ValidationError("profile name must use a namespaced form such as 'web/mp4-compatible'")
        if self.profile_version <= 0:
            raise ValidationError("profile_version must be a positive integer")
        if not self.description.strip() or not self.workflow.strip():
            raise ValidationError("profile description and workflow must not be empty")
        if not _is_json_value(self.options):
            raise ValidationError("profile options must contain only JSON-compatible values")
        if any(not value or ":" not in value for value in self.required_capabilities):
            raise ValidationError("required capabilities must use a kind:name form such as 'encoder:libx264'")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Profile:
        """Create a profile while rejecting unknown and missing fields."""
        unknown = sorted(set(payload) - _PROFILE_FIELDS)
        if unknown:
            raise ValidationError(f"Unknown profile fields: {', '.join(unknown)}")
        required = {"schema_version", "name", "profile_version", "description", "workflow", "options"}
        missing = sorted(required - set(payload))
        if missing:
            raise ValidationError(f"Missing profile fields: {', '.join(missing)}")
        capabilities = payload.get("required_capabilities", [])
        if not isinstance(capabilities, list) or not all(isinstance(value, str) for value in capabilities):
            raise ValidationError("required_capabilities must be an array of strings")
        if not isinstance(payload["options"], dict):
            raise ValidationError("options must be an object")
        if not isinstance(payload["profile_version"], int) or isinstance(payload["profile_version"], bool):
            raise ValidationError("profile_version must be an integer")
        return cls(
            schema_version=str(payload["schema_version"]),
            name=str(payload["name"]),
            profile_version=payload["profile_version"],
            description=str(payload["description"]),
            workflow=str(payload["workflow"]),
            options=dict(payload["options"]),
            required_capabilities=tuple(capabilities),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["required_capabilities"] = list(self.required_capabilities)
        return data


BUILTIN_PROFILES = (
    Profile(
        name="web/mp4-compatible",
        profile_version=1,
        description="Broad browser playback with H.264 video, AAC audio, yuv420p pixels, and fast start.",
        workflow="convert",
        options={
            "video_codec": "libx264",
            "audio_codec": "aac",
            "pixel_format": "yuv420p",
            "movflags": "+faststart",
        },
        required_capabilities=("encoder:libx264", "encoder:aac", "muxer:mp4"),
    ),
    Profile(
        name="web/small-upload",
        profile_version=1,
        description="A conservative H.264/AAC compression starting point for upload-limited video.",
        workflow="compress",
        options={"crf": 28, "preset": "medium", "video_codec": "libx264", "audio_bitrate": "128k"},
        required_capabilities=("encoder:libx264", "encoder:aac", "muxer:mp4"),
    ),
    Profile(
        name="audio/podcast-speech",
        profile_version=1,
        description="Speech normalization targeting -16 LUFS stereo delivery with a true-peak ceiling.",
        workflow="normalize-audio",
        options={"lufs": -16.0, "true_peak": -1.5, "loudness_range": 11.0, "audio_bitrate": "192k"},
        required_capabilities=("filter:loudnorm", "encoder:aac"),
    ),
    Profile(
        name="subtitles/accessibility",
        profile_version=1,
        description="Add a language-labelled subtitle track while copying existing video and audio streams.",
        workflow="subtitles/add",
        options={"language": "und", "video_codec": "copy", "audio_codec": "copy", "subtitle_codec": "mov_text"},
        required_capabilities=("encoder:mov_text", "muxer:mp4"),
    ),
    Profile(
        name="archive/mezzanine",
        profile_version=1,
        description="Lossless FFV1 video and FLAC audio in Matroska for an archival mezzanine copy.",
        workflow="convert",
        options={"video_codec": "ffv1", "audio_codec": "flac", "container": "matroska"},
        required_capabilities=("encoder:ffv1", "encoder:flac", "muxer:matroska"),
    ),
)


class ProfileRegistry:
    """Resolve built-in profiles and strictly validate local profile files."""

    def __init__(self) -> None:
        self._profiles = {profile.name: profile for profile in BUILTIN_PROFILES}

    def list(self) -> tuple[Profile, ...]:
        return tuple(self._profiles[name] for name in sorted(self._profiles))

    def get(self, name: str) -> Profile:
        try:
            return self._profiles[name]
        except KeyError as exc:
            raise ValidationError(f"Unknown profile: {name}") from exc

    def load_file(self, path: str | Path) -> Profile:
        """Load one strict versioned profile from JSON or TOML."""
        profile_path = Path(path)
        if not profile_path.is_file():
            raise ValidationError(f"Profile file does not exist: {profile_path}")
        try:
            if profile_path.suffix.lower() == ".json":
                payload = json.loads(profile_path.read_text(encoding="utf-8"))
            elif profile_path.suffix.lower() == ".toml":
                try:
                    import tomllib
                except ModuleNotFoundError:  # pragma: no cover - Python 3.10 runtime
                    import tomli as tomllib

                with profile_path.open("rb") as handle:
                    payload = tomllib.load(handle)
            else:
                raise ValidationError("Profile files must use .json or .toml")
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValidationError(f"Invalid profile file {profile_path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValidationError("Profile document must be an object/table")
        return Profile.from_dict(payload)
