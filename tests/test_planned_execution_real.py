"""Real-media contracts for the shared typed planner and execution engine."""

from __future__ import annotations

import pytest

from pyffmpegcore import CompressOptions, FFmpegRunner, FFprobeRunner, PreflightEngine, WorkflowPlanner
from tests.media_utils import ensure_downloaded_media


@pytest.mark.real_media
def test_planned_thumbnail_preflights_executes_and_emits_progress(tmp_path):
    media = ensure_downloaded_media()
    output = tmp_path / "nested" / "thumbnail.jpg"
    plan = WorkflowPlanner().thumbnail(
        str(media["video_mp4_h264_1080p"]),
        str(output),
        timestamp="00:00:00.2",
        width=160,
    )
    events = []

    preflight = PreflightEngine().check(plan)
    result = FFmpegRunner().execute_plan(plan, progress_callback=events.append)

    assert preflight.ok
    assert result.succeeded, result.stderr
    assert result.progress is not None and result.progress.status == "end"
    assert events and events[-1] == result.progress
    image = FFprobeRunner().probe(str(output))["video"]
    assert image["width"] == 160


@pytest.mark.real_media
def test_planned_target_size_uses_two_clean_steps_and_stays_under_limit(tmp_path, monkeypatch):
    media = ensure_downloaded_media()
    output = tmp_path / "compressed.mp4"
    workspace = tmp_path / "two-pass-workspace"

    def create_workspace(**_kwargs):
        workspace.mkdir()
        return str(workspace)

    monkeypatch.setattr("pyffmpegcore.executor.tempfile.mkdtemp", create_workspace)
    target_bytes = 500_000
    plan = WorkflowPlanner().compress(
        str(media["video_mp4_h264_1080p"]),
        str(output),
        CompressOptions(
            target_size_bytes=target_bytes,
            minimum_video_bitrate=50_000,
            threads=1,
        ),
    )

    result = FFmpegRunner().execute_plan(plan)

    assert [step.name for step in plan.steps] == ["analysis-pass", "encode-pass"]
    assert result.succeeded, result.stderr
    assert output.stat().st_size <= target_bytes
    assert not workspace.exists()


@pytest.mark.real_media
def test_planned_concat_materializes_manifest_without_orphans(tmp_path, monkeypatch):
    media = ensure_downloaded_media()
    output = tmp_path / "joined.mp4"
    workspace = tmp_path / "concat-workspace"

    def create_workspace(**_kwargs):
        workspace.mkdir()
        return str(workspace)

    monkeypatch.setattr("pyffmpegcore.executor.tempfile.mkdtemp", create_workspace)
    source = str(media["video_mp4_h264_1080p"])
    plan = WorkflowPlanner().concat([source, source], str(output), mode="copy")

    result = FFmpegRunner().execute_plan(plan)

    assert result.succeeded, result.stderr
    assert output.is_file()
    assert not workspace.exists()
