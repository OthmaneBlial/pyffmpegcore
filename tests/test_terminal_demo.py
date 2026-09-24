"""The terminal demo validator rejects abbreviated, fake, or private recordings."""

import json
from pathlib import Path

import pytest

from scripts.validate_terminal_demo import validate_recording

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_TRANSCRIPT = """
$ demo-env/bin/python -m pip install pyffmpegcore==0.2.0
Successfully installed pyffmpegcore-0.2.0
pyffmpegcore 0.2.0
ffmpeg: OK
Smoke test: PASS
Plan 1.0
Progress: 100% complete
Output: media/web.mp4
Receipt: media/web.receipt.json
Valid receipt: schema 1.0
No upload. No telemetry.
"""


def write_cast(path: Path, *, duration: float, transcript: str = REQUIRED_TRANSCRIPT) -> None:
    lines = [json.dumps({"version": 2, "width": 100, "height": 32})]
    lines.append(json.dumps([duration, "o", transcript]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_terminal_recorder_installs_hash_locked_wheel():
    script = (REPO_ROOT / "scripts" / "record_terminal_demo.sh").read_text(encoding="utf-8")

    assert (
        "asciinema==2.4.0 \\\n    --hash=sha256:249ccf108509d643ddaf38979dac48c99e9e251f597173d8553a30d7a6423104\n"
    ) in script
    assert "--only-binary=:all:" in script
    assert "--require-hashes" in script
    assert '-r "$requirements_file"' in script


def test_terminal_demo_accepts_complete_realistic_contract(tmp_path):
    cast_path = tmp_path / "demo.cast"
    write_cast(cast_path, duration=72.5)

    duration, transcript = validate_recording(cast_path, expected_version="0.2.0")

    assert duration == 72.5
    assert "Smoke test: PASS" in transcript


@pytest.mark.parametrize("duration", [59.9, 90.1])
def test_terminal_demo_rejects_wrong_duration(tmp_path, duration):
    cast_path = tmp_path / "demo.cast"
    write_cast(cast_path, duration=duration)

    with pytest.raises(ValueError, match="60–90"):
        validate_recording(cast_path, expected_version="0.2.0")


def test_terminal_demo_rejects_private_home_paths(tmp_path):
    cast_path = tmp_path / "demo.cast"
    write_cast(cast_path, duration=70, transcript=REQUIRED_TRANSCRIPT + "/Users/example/private.mov")

    with pytest.raises(ValueError, match="private home path"):
        validate_recording(cast_path, expected_version="0.2.0")
