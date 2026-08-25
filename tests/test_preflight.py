"""Non-mutating preflight contracts."""

from __future__ import annotations

from unittest.mock import patch

from pyffmpegcore import ExecutionPlan, ExecutionPolicy, MediaInfo, OverwritePolicy, StreamInfo
from pyffmpegcore.capabilities import CapabilityInventory
from pyffmpegcore.preflight import PreflightEngine, _input_scheme


def inventory(*, encoders=("aac", "libx264", "mpeg4"), filters=("scale",)):
    return CapabilityInventory(
        binary="ffmpeg",
        encoders=encoders,
        decoders=("h264",),
        filters=filters,
        muxers=("image2", "mp4"),
        demuxers=("concat", "mov"),
        input_protocols=("file", "https"),
        output_protocols=("file", "pipe"),
        hardware_accelerators=(),
    )


def test_preflight_checks_streams_output_disk_and_collision_without_mutation(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    output = tmp_path / "not-created" / "output.mp4"
    plan = ExecutionPlan(
        workflow="convert",
        command=("ffmpeg", "-i", str(source), str(output)),
        inputs=(str(source),),
        outputs=(str(output),),
        required_capabilities=("encoder:libx264",),
        metadata={"required_stream_types": ["video"], "estimated_output_bytes": 1},
    )
    media = MediaInfo(path=str(source), streams=(StreamInfo(index=0, codec_type="video", codec_name="h264"),))

    with patch("pyffmpegcore.preflight.FFprobeRunner.probe_media", return_value=media):
        report = PreflightEngine(
            inventory=inventory(),
            executable_resolver=lambda _binary: "/usr/bin/ffmpeg",
        ).check(plan)

    assert report.ok
    assert report.to_dict()["schema_version"] == "1.0"
    assert "Preflight PASS" in report.render()
    assert not output.parent.exists()


def test_preflight_explains_missing_capability_with_available_fallback(tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"x")
    plan = ExecutionPlan(
        workflow="convert",
        command=("ffmpeg", "-i", str(source), str(tmp_path / "output.mp4")),
        inputs=(str(source),),
        outputs=(str(tmp_path / "output.mp4"),),
        required_capabilities=("encoder:libx264",),
    )

    report = PreflightEngine(
        inventory=inventory(encoders=("aac", "mpeg4")),
        executable_resolver=lambda _binary: "/usr/bin/ffmpeg",
    ).check(plan)

    missing = next(check for check in report.checks if check.name == "capability/encoder:libx264")
    assert not report.ok
    assert missing.message == "Missing required capability: encoder:libx264"
    assert "tested fallback encoder:mpeg4" in (missing.hint or "")


def test_preflight_refuses_collision_and_corrupted_input(tmp_path):
    source = tmp_path / "corrupt.mp4"
    source.write_bytes(b"not media")
    output = tmp_path / "output.mp4"
    output.write_bytes(b"keep")
    plan = ExecutionPlan(
        workflow="convert",
        command=("ffmpeg", "-i", str(source), str(output)),
        inputs=(str(source),),
        outputs=(str(output),),
        policy=ExecutionPolicy(overwrite=OverwritePolicy.REFUSE),
        metadata={"required_stream_types": ["video"]},
    )

    with patch("pyffmpegcore.preflight.FFprobeRunner.probe_media", side_effect=RuntimeError("invalid data")):
        report = PreflightEngine(
            inventory=inventory(),
            executable_resolver=lambda _binary: "/usr/bin/ffmpeg",
        ).check(plan)

    assert not report.ok
    assert any(check.name.startswith("probe/") and check.status == "fail" for check in report.checks)
    assert any(check.name.startswith("collision/") and check.status == "fail" for check in report.checks)
    assert output.read_bytes() == b"keep"


def test_windows_drive_path_is_not_treated_as_a_remote_protocol():
    assert _input_scheme(r"C:\media\clip.mp4") is None
    assert _input_scheme("https://example.test/clip.mp4") == "https"
