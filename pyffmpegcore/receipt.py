"""Privacy-aware, versioned execution receipts and validation."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from . import __version__
from .errors import ValidationError
from .probe import FFprobeRunner
from .workflow import WorkflowBatch

RECEIPT_SCHEMA_VERSION = "1.0"
_SECRET_ASSIGNMENT = re.compile(r"(?i)\b(authorization|api[-_]?key|password|secret|token)\s*([=:])\s*([^\s,;&]+)")
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")


def _redact_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if not parsed.scheme or not parsed.netloc:
        return value
    host = parsed.hostname or "<host>"
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    basename = Path(parsed.path).name
    path = f"/<path>/{basename}" if basename else "/<path>"
    query = "<redacted>" if parsed.query else ""
    return urlunsplit((parsed.scheme, host, path, query, ""))


def _private_path_map(document: Any) -> dict[str, str]:
    paths: set[str] = set()

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                collect(child)
        elif isinstance(value, str) and Path(value).is_absolute():
            paths.add(value)

    collect(document)
    return {value: f"<path>/{Path(value).name}" for value in sorted(paths, key=len, reverse=True)}


def redact_receipt_value(value: Any, path_map: dict[str, str] | None = None) -> Any:
    """Recursively redact credentials, secret assignments, and private path components."""
    replacements = path_map or _private_path_map(value)
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            if re.search(r"(?i)(authorization|api[-_]?key|password|secret|token)", str(key)):
                result[key] = "<redacted>"
            else:
                result[key] = redact_receipt_value(child, replacements)
        return result
    if isinstance(value, (list, tuple)):
        return [redact_receipt_value(child, replacements) for child in value]
    if not isinstance(value, str):
        return value

    redacted = value
    for private, replacement in replacements.items():
        redacted = redacted.replace(private, replacement)
    if "://" in redacted and redacted == value:
        redacted = _redact_url(redacted)
    redacted = _BEARER.sub("Bearer <redacted>", redacted)
    return _SECRET_ASSIGNMENT.sub(lambda match: f"{match.group(1)}{match.group(2)}<redacted>", redacted)


def _version_line(binary: str) -> str | None:
    try:
        result = subprocess.run(
            [binary, "-version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = result.stdout.strip() or result.stderr.strip()
    return text.splitlines()[0] if text else None


def _probe_summary(path: str | None, runner: FFprobeRunner) -> dict[str, Any] | None:
    if path is None or "://" in path or not Path(path).is_file():
        return None
    try:
        media = runner.probe_media(path)
    except (OSError, RuntimeError, ValueError):
        return None
    return {
        "path": path,
        "format_name": media.format_name,
        "duration": media.duration,
        "size_bytes": media.size,
        "bit_rate": media.bit_rate,
        "streams": [
            {
                "index": stream.index,
                "type": stream.codec_type,
                "codec": stream.codec_name,
                "width": stream.width,
                "height": stream.height,
                "sample_rate": stream.sample_rate,
                "channels": stream.channels,
                "language": stream.language,
                "rotation": stream.rotation,
            }
            for stream in media.streams
        ],
        "chapter_count": len(media.chapters),
    }


def _hash_file(path: str, algorithm: str = "sha256") -> dict[str, str] | None:
    candidate = Path(path)
    if not candidate.is_file():
        return None
    digest = hashlib.new(algorithm)
    with candidate.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": path, "algorithm": algorithm, "digest": digest.hexdigest()}


def validate_receipt(document: Any) -> tuple[str, ...]:
    """Return stable schema/semantic validation errors without mutating the document."""
    if not isinstance(document, dict):
        return ("receipt must be a JSON object",)
    errors = []
    if document.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {RECEIPT_SCHEMA_VERSION!r}")
    if not isinstance(document.get("privacy"), dict):
        errors.append("privacy must be an object")
    if not isinstance(document.get("plan"), dict):
        errors.append("plan must be an object")
    if not isinstance(document.get("tools"), dict):
        errors.append("tools must be an object")
    summary = document.get("summary")
    if not isinstance(summary, dict):
        errors.append("summary must be an object")
    elif not all(isinstance(summary.get(key), int) for key in ("total", "succeeded", "failed")):
        errors.append("summary counts must be integers")
    items = document.get("items")
    if not isinstance(items, list) or not items:
        errors.append("items must be a non-empty array")
    elif any(
        not isinstance(item, dict)
        or not isinstance(item.get("result"), dict)
        or not isinstance(item.get("proof"), dict)
        for item in items
    ):
        errors.append("each item must contain result and proof objects")
    hashes = document.get("content_hashes", [])
    if not isinstance(hashes, list) or any(
        not isinstance(item, dict) or item.get("algorithm") not in hashlib.algorithms_available for item in hashes
    ):
        errors.append("content_hashes must use explicit supported algorithms")
    return tuple(errors)


@dataclass(frozen=True, slots=True)
class RunReceipt:
    """Validated schema 1.0 receipt suitable for storage or bug reports."""

    document: dict[str, Any]

    def __post_init__(self) -> None:
        errors = validate_receipt(self.document)
        if errors:
            raise ValidationError("invalid receipt: " + "; ".join(errors))

    def to_dict(self) -> dict[str, Any]:
        return dict(self.document)

    def to_json(self) -> str:
        return json.dumps(self.document, indent=2, ensure_ascii=False) + "\n"

    def write(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(self.to_json(), encoding="utf-8")
        return destination

    @classmethod
    def read(cls, path: str | Path) -> RunReceipt:
        try:
            document = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValidationError(f"unable to read receipt: {exc}") from exc
        return cls(document)


class ReceiptBuilder:
    """Build redacted receipts from the same prepared workflow and stable results."""

    def __init__(self, *, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def build(self, batch: WorkflowBatch, *, hash_content: bool = False) -> RunReceipt:
        """Create a private-by-default receipt; content hashes are explicit opt-in."""
        probe = FFprobeRunner(self.ffprobe_path)
        items = []
        for item in batch.items:
            items.append(
                {
                    "input_probe": _probe_summary(item.input, probe),
                    "output_probe": _probe_summary(item.output, probe),
                    "proof": item.proof,
                    "preflight": item.preflight.to_dict(),
                    "result": {
                        "workflow": item.result.workflow,
                        "status": item.result.status.value,
                        "exit_category": item.result.exit_category,
                        "returncode": item.result.returncode,
                        "elapsed_seconds": item.result.elapsed_seconds,
                        "progress": item.result.progress.to_dict() if item.result.progress else None,
                        "warnings": list(item.result.warnings),
                    },
                }
            )

        hashes = []
        if hash_content:
            for path in dict.fromkeys((*batch.prepared.plan.inputs, *batch.prepared.plan.outputs)):
                hashed = _hash_file(path)
                if hashed is not None:
                    hashes.append(hashed)

        raw = {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "privacy": {
                "paths": "basename-only",
                "url_credentials": "redacted",
                "url_queries": "redacted",
                "secret_assignments": "redacted",
                "content_hashing": "sha256-opt-in" if hash_content else "disabled",
            },
            "plan": batch.prepared.plan.to_dict(),
            "tools": {
                "pyffmpegcore": __version__,
                "python": platform.python_version(),
                "platform": platform.platform(),
                "ffmpeg": _version_line(self.ffmpeg_path),
                "ffprobe": _version_line(self.ffprobe_path),
            },
            "summary": {
                "total": len(batch.items),
                "succeeded": batch.succeeded_count,
                "failed": batch.failed_count,
            },
            "items": items,
            "content_hashes": hashes,
        }
        return RunReceipt(redact_receipt_value(raw))


def build_bug_report(receipt: RunReceipt, doctor: dict[str, Any]) -> dict[str, Any]:
    """Combine already redacted evidence without requiring private media."""
    return {
        "schema_version": "1.0",
        "doctor": redact_receipt_value(doctor),
        "receipt": receipt.to_dict(),
    }


def migrate_receipt(document: dict[str, Any], target_version: str = RECEIPT_SCHEMA_VERSION) -> RunReceipt:
    """Migrate and canonicalize a receipt; 1.0 is the first and only current schema."""
    source_version = document.get("schema_version") if isinstance(document, dict) else None
    if target_version != RECEIPT_SCHEMA_VERSION:
        raise ValidationError(f"unsupported target receipt schema: {target_version}")
    if source_version != RECEIPT_SCHEMA_VERSION:
        raise ValidationError(f"no receipt migration path from {source_version!r} to {target_version!r}")
    return RunReceipt(redact_receipt_value(deepcopy(document)))
