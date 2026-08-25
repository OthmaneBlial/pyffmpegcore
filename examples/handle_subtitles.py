"""Add, extract, or burn subtitles through shared typed plans."""

from __future__ import annotations

from examples._shared import run_plan
from pyffmpegcore import FFprobeRunner, WorkflowEngine


def extract_subtitles(video_file: str, output_file: str, stream_index: int = 0) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.subtitles(
        "extract",
        video_file,
        output_file,
        stream_index=stream_index,
    )
    return run_plan(engine, plan).succeeded


def burn_subtitles(
    video_file: str,
    subtitle_file: str,
    output_file: str,
    font_size: int = 24,
    font_color: str = "&HFFFFFF",
) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.subtitles(
        "burn",
        video_file,
        output_file,
        subtitle_file=subtitle_file,
        font_size=font_size,
        font_color=font_color,
    )
    return run_plan(engine, plan).succeeded


def add_subtitle_track(
    video_file: str,
    subtitle_file: str,
    output_file: str,
    language: str = "eng",
) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.subtitles(
        "add",
        video_file,
        output_file,
        subtitle_file=subtitle_file,
        language=language,
    )
    return run_plan(engine, plan).succeeded


def get_subtitle_info(video_file: str) -> list[dict]:
    metadata = FFprobeRunner().probe(video_file)
    return [stream for stream in metadata.get("streams", []) if stream.get("codec_type") == "subtitle"]


def main() -> None:
    if add_subtitle_track("input.mp4", "captions.srt", "subtitled.mp4"):
        print("Created subtitled.mp4")


if __name__ == "__main__":
    main()
