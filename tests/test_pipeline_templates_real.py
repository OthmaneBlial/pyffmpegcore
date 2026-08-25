"""Golden real-media contracts for the three published declarative pipelines."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyffmpegcore import PipelineCompiler, PipelinePreflightEngine, PipelineRunner, PipelineSpec
from tests.media_utils import ensure_downloaded_media

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.real_media
@pytest.mark.parametrize(
    ("template", "variables", "expected"),
    [
        (
            "web-publish.json",
            {"INPUT": "rich_streams_mkv"},
            {"video.mp4", "poster.jpg"},
        ),
        (
            "podcast-package.toml",
            {"INPUT": "audio_wav_pcm"},
            {"episode.m4a", "waveform.png"},
        ),
        (
            "video-thumbnails-subtitles.json",
            {"INPUT": "video_mov_h264_640x360", "CAPTIONS": "subtitles_srt"},
            {"captioned.mp4", "video.mp4", "poster.jpg"},
        ),
    ],
)
def test_published_pipeline_template_runs_real_media(tmp_path, template, variables, expected):
    fixtures = ensure_downloaded_media()
    selected = {name: str(fixtures[fixture]) for name, fixture in variables.items()}
    selected["OUTPUT_DIR"] = str(tmp_path / template)
    pipeline = PipelineCompiler().compile(
        PipelineSpec.read(REPO_ROOT / "pipelines" / template),
        variables=selected,
        cache_enabled=False,
    )

    prepared = PipelinePreflightEngine().prepare(pipeline)
    result = PipelineRunner().run(pipeline)

    assert prepared.ok
    assert result.succeeded, [item.detail for item in result.items]
    assert {path.name for path in (tmp_path / template).iterdir()} == expected
