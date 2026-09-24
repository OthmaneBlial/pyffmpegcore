"""Non-mutating preflight contracts."""

from __future__ import annotations

import os
from collections import namedtuple
from unittest.mock import patch

import pytest

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


def test_preflight_rejects_concat_copy_when_stream_layouts_differ(tmp_path):
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.write_bytes(b"a")
    second.write_bytes(b"b")
    output = tmp_path / "joined.mp4"
    plan = ExecutionPlan(
        workflow="concat/copy",
        command=("ffmpeg", "-f", "concat", "-i", "manifest", "-c", "copy", str(output)),
        inputs=(str(first), str(second)),
        outputs=(str(output),),
        metadata={"required_stream_types": ["video"], "estimated_output_bytes": 1},
    )
    media = {
        str(first): MediaInfo(
            path=str(first),
            streams=(StreamInfo(index=0, codec_type="video", codec_name="h264", width=1920, height=1080),),
        ),
        str(second): MediaInfo(
            path=str(second),
            streams=(StreamInfo(index=0, codec_type="video", codec_name="h264", width=1280, height=720),),
        ),
    }

    with patch("pyffmpegcore.preflight.FFprobeRunner.probe_media", side_effect=lambda path: media[path]):
        report = PreflightEngine(
            inventory=inventory(),
            executable_resolver=lambda _binary: "/usr/bin/ffmpeg",
        ).check(plan)

    compatibility = next(check for check in report.checks if check.name == "concat/copy-compatibility")
    assert not report.ok
    assert compatibility.status == "fail"
    assert "stream metadata differs" in compatibility.message.lower()
    assert "normalize" in (compatibility.hint or "").lower()
    assert not output.exists()


def test_preflight_reports_matching_concat_copy_stream_metadata(tmp_path):
    inputs = (tmp_path / "first.mp4", tmp_path / "second.mp4")
    for path in inputs:
        path.write_bytes(b"a")
    output = tmp_path / "joined.mp4"
    plan = ExecutionPlan(
        workflow="concat/copy",
        command=("ffmpeg", "-f", "concat", "-i", "manifest", "-c", "copy", str(output)),
        inputs=tuple(map(str, inputs)),
        outputs=(str(output),),
        metadata={"required_stream_types": ["video"], "estimated_output_bytes": 1},
    )
    media = MediaInfo(
        path=str(inputs[0]),
        streams=(StreamInfo(index=0, codec_type="video", codec_name="h264", width=1920, height=1080),),
    )

    with patch("pyffmpegcore.preflight.FFprobeRunner.probe_media", return_value=media):
        report = PreflightEngine(
            inventory=inventory(),
            executable_resolver=lambda _binary: "/usr/bin/ffmpeg",
        ).check(plan)

    compatibility = next(check for check in report.checks if check.name == "concat/copy-compatibility")
    assert report.ok
    assert compatibility.status == "pass"
    assert "packet-level compatibility is not guaranteed" in compatibility.message


def test_preflight_warns_when_concat_copy_inputs_are_remote():
    plan = ExecutionPlan(
        workflow="concat/copy",
        command=("ffmpeg", "-f", "concat", "-i", "manifest", "-c", "copy", "joined.mp4"),
        inputs=("https://media.example/one.mp4", "https://media.example/two.mp4"),
        outputs=("joined.mp4",),
        metadata={"required_stream_types": ["video"], "estimated_output_bytes": 1},
    )

    report = PreflightEngine(
        inventory=inventory(),
        executable_resolver=lambda _binary: "/usr/bin/ffmpeg",
    ).check(plan)

    compatibility = next(check for check in report.checks if check.name == "concat/copy-compatibility")
    assert report.ok
    assert compatibility.status == "warn"
    assert "https://media.example" not in compatibility.message


@pytest.mark.parametrize(("second_width", "expected_status"), [(1280, "fail"), (1920, "pass")])
def test_preflight_checks_concat_reencode_dimensions(tmp_path, second_width, expected_status):
    inputs = (tmp_path / "first.mp4", tmp_path / "second.mp4")
    for path in inputs:
        path.write_bytes(b"a")
    output = tmp_path / "joined.mp4"
    plan = ExecutionPlan(
        workflow="concat/reencode",
        command=("ffmpeg", "-i", str(inputs[0]), "-i", str(inputs[1]), "-filter_complex", "concat", str(output)),
        inputs=tuple(map(str, inputs)),
        outputs=(str(output),),
        metadata={"required_stream_types": ["video", "audio"], "estimated_output_bytes": 1},
    )
    media = {
        str(inputs[0]): MediaInfo(
            path=str(inputs[0]),
            streams=(
                StreamInfo(index=0, codec_type="video", codec_name="h264", width=1920, height=1080),
                StreamInfo(index=1, codec_type="audio", codec_name="aac", sample_rate=48000, channels=2),
            ),
        ),
        str(inputs[1]): MediaInfo(
            path=str(inputs[1]),
            streams=(
                StreamInfo(index=0, codec_type="video", codec_name="vp9", width=second_width, height=1080),
                StreamInfo(index=1, codec_type="audio", codec_name="opus", sample_rate=48000, channels=2),
            ),
        ),
    }

    with patch("pyffmpegcore.preflight.FFprobeRunner.probe_media", side_effect=lambda path: media[path]):
        report = PreflightEngine(
            inventory=inventory(filters=("concat", "setpts", "asetpts", "scale")),
            executable_resolver=lambda _binary: "/usr/bin/ffmpeg",
        ).check(plan)

    compatibility = next(check for check in report.checks if check.name == "concat/reencode-compatibility")
    assert ("pass" if report.ok else "fail") == expected_status
    assert compatibility.status == expected_status
    if expected_status == "fail":
        assert "dimensions differ" in compatibility.message
        assert "Resize each clip" in (compatibility.hint or "")
        assert not output.exists()


def test_preflight_warns_when_concat_reencode_omits_additional_stream_types(tmp_path):
    inputs = (tmp_path / "first.mp4", tmp_path / "second.mp4")
    for path in inputs:
        path.write_bytes(b"a")
    plan = ExecutionPlan(
        workflow="concat/reencode",
        command=("ffmpeg", "-i", str(inputs[0]), "-i", str(inputs[1]), "-filter_complex", "concat"),
        inputs=tuple(map(str, inputs)),
        outputs=(str(tmp_path / "joined.mp4"),),
        metadata={"required_stream_types": ["video", "audio"]},
    )
    media = {
        str(inputs[0]): MediaInfo(
            path=str(inputs[0]),
            streams=(
                StreamInfo(index=0, codec_type="video", width=1920, height=1080),
                StreamInfo(index=1, codec_type="audio"),
                StreamInfo(index=2, codec_type="audio"),
                StreamInfo(index=3, codec_type="subtitle"),
            ),
        ),
        str(inputs[1]): MediaInfo(
            path=str(inputs[1]),
            streams=(
                StreamInfo(index=0, codec_type="video", width=1920, height=1080),
                StreamInfo(index=1, codec_type="audio"),
            ),
        ),
    }

    with patch("pyffmpegcore.preflight.FFprobeRunner.probe_media", side_effect=lambda path: media[path]):
        report = PreflightEngine(
            inventory=inventory(filters=("concat", "setpts", "asetpts", "scale")),
            executable_resolver=lambda _binary: "/usr/bin/ffmpeg",
        ).check(plan)

    selection = next(check for check in report.checks if check.name == "concat/reencode-stream-selection")
    assert report.ok
    assert selection.status == "warn"
    assert "audio, subtitle" in selection.message
    assert "extract and convert" in (selection.hint or "")


def test_preflight_warns_that_remote_concat_reencode_tracks_are_uninspected():
    plan = ExecutionPlan(
        workflow="concat/reencode",
        command=("ffmpeg", "-i", "https://user:secret@example.test/one.mp4", "-filter_complex", "concat"),
        inputs=("https://user:secret@example.test/one.mp4", "https://media.example/two.mp4"),
        outputs=("joined.mp4",),
        metadata={"required_stream_types": ["video", "audio"]},
    )

    report = PreflightEngine(
        inventory=inventory(filters=("concat", "setpts", "asetpts", "scale")),
        executable_resolver=lambda _binary: "/usr/bin/ffmpeg",
    ).check(plan)

    selection = next(check for check in report.checks if check.name == "concat/reencode-stream-selection")
    assert report.ok
    assert selection.status == "warn"
    assert "Remote input tracks cannot be inspected" in selection.message
    assert "secret" not in report.render()


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


def test_preflight_rejects_missing_filter_before_mutation(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    output = tmp_path / "output.mp4"
    plan = ExecutionPlan(
        workflow="resize",
        command=("ffmpeg", "-i", str(source), "-vf", "scale=10:10", str(output)),
        inputs=(str(source),),
        outputs=(str(output),),
        required_capabilities=("filter:scale",),
    )

    report = PreflightEngine(
        inventory=inventory(filters=()),
        executable_resolver=lambda _binary: "/usr/bin/ffmpeg",
    ).check(plan)

    assert not report.ok
    assert any(check.name == "capability/filter:scale" and check.status == "fail" for check in report.checks)
    assert not output.exists()


def test_preflight_reports_capability_inspection_timeout():
    plan = ExecutionPlan(workflow="convert", command=("ffmpeg",), inputs=(), outputs=())

    with patch(
        "pyffmpegcore.preflight.CapabilityInventory.inspect",
        side_effect=RuntimeError("FFmpeg capability listing timed out after 5 seconds (-encoders)."),
    ):
        report = PreflightEngine(executable_resolver=lambda _binary: "/usr/bin/ffmpeg").check(plan)

    failed = next(check for check in report.checks if check.name == "capabilities")
    assert failed.status == "fail"
    assert "timed out after 5 seconds" in failed.message
    assert "rerun preflight" in failed.hint


def test_preflight_rejects_full_disk_before_creating_output(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    output = tmp_path / "nested" / "output.mp4"
    plan = ExecutionPlan(
        workflow="convert",
        command=("ffmpeg", "-i", str(source), str(output)),
        inputs=(str(source),),
        outputs=(str(output),),
        metadata={"estimated_output_bytes": 10_000},
    )
    DiskUsage = namedtuple("DiskUsage", "total used free")

    with patch("pyffmpegcore.preflight.shutil.disk_usage", return_value=DiskUsage(10_000, 9_999, 1)):
        report = PreflightEngine(
            inventory=inventory(),
            executable_resolver=lambda _binary: "/usr/bin/ffmpeg",
        ).check(plan)

    disk = next(check for check in report.checks if check.name.startswith("disk/"))
    assert not report.ok
    assert disk.status == "fail"
    assert "need about 10000 bytes, have 1" in disk.message
    assert not output.parent.exists()


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
    assert "--force" in next(check.hint for check in report.checks if check.name.startswith("collision/"))
    assert output.read_bytes() == b"keep"


def test_preflight_explains_unwritable_output_parent(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"media")
    output = tmp_path / "output.mp4"
    plan = ExecutionPlan(
        workflow="convert",
        command=("ffmpeg", "-i", str(source), str(output)),
        inputs=(str(source),),
        outputs=(str(output),),
    )
    actual_access = os.access

    def access(path, mode):
        if path == tmp_path and mode == os.W_OK:
            return False
        return actual_access(path, mode)

    with patch("pyffmpegcore.preflight.os.access", side_effect=access):
        report = PreflightEngine(
            inventory=inventory(),
            executable_resolver=lambda _binary: "/usr/bin/ffmpeg",
        ).check(plan)

    output_check = next(check for check in report.checks if check.name.startswith("output/"))
    assert not report.ok
    assert output_check.status == "fail"
    assert "writable directory" in (output_check.hint or "")


def test_windows_drive_path_is_not_treated_as_a_remote_protocol():
    assert _input_scheme(r"C:\media\clip.mp4") is None
    assert _input_scheme("https://example.test/clip.mp4") == "https"


def test_preflight_redacts_remote_input_label_and_rejects_remote_output(tmp_path):
    secret = "https://user:do-not-log@example.invalid/media.mp4?token=do-not-log"
    plan = ExecutionPlan(
        workflow="convert",
        command=("ffmpeg", "-i", secret, str(tmp_path / "web.mp4")),
        inputs=(secret,),
        outputs=(str(tmp_path / "web.mp4"),),
    )
    report = PreflightEngine(
        inventory=inventory(),
        executable_resolver=lambda _binary: "/usr/bin/ffmpeg",
    ).check(plan)
    assert report.ok
    assert "do-not-log" not in report.render()
    assert any(check.name == "input/https://<redacted>" for check in report.checks)

    remote_output = ExecutionPlan(
        workflow="convert",
        command=("ffmpeg", "-i", str(tmp_path / "source.mp4"), secret),
        inputs=(),
        outputs=(secret,),
    )
    output_report = PreflightEngine(
        inventory=inventory(),
        executable_resolver=lambda _binary: "/usr/bin/ffmpeg",
    ).check(remote_output)
    assert not output_report.ok
    assert "do-not-log" not in output_report.render()
    assert any(check.name == "output/remote" and check.status == "fail" for check in output_report.checks)


def test_preflight_applies_stream_requirements_per_input(tmp_path):
    video = tmp_path / "video.mp4"
    subtitle = tmp_path / "captions.srt"
    video.write_bytes(b"video")
    subtitle.write_text("captions", encoding="utf-8")
    plan = ExecutionPlan(
        workflow="subtitles/add",
        command=("ffmpeg", "-i", str(video), "-i", str(subtitle)),
        inputs=(str(video), str(subtitle)),
        outputs=(str(tmp_path / "output.mp4"),),
        metadata={"input_stream_requirements": {str(video): ["video"], str(subtitle): ["subtitle"]}},
    )

    def probe_media(path):
        kind = "subtitle" if path.endswith(".srt") else "video"
        return MediaInfo(path=path, streams=(StreamInfo(index=0, codec_type=kind),))

    with patch("pyffmpegcore.preflight.FFprobeRunner.probe_media", side_effect=probe_media):
        report = PreflightEngine(
            inventory=inventory(encoders=("mov_text",), filters=()),
            executable_resolver=lambda _binary: "/usr/bin/ffmpeg",
        ).check(plan)

    assert report.ok
