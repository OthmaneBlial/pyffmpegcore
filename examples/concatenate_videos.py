"""Concatenate matching or mixed clips through shared plans."""

from __future__ import annotations

from examples._shared import run_plan
from pyffmpegcore import FFprobeRunner, WorkflowEngine


def concatenate_videos_basic(video_files: list[str], output_file: str) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.concat(video_files, output_file, mode="copy")
    return run_plan(engine, plan).succeeded


def concatenate_videos_reencode(
    video_files: list[str],
    output_file: str,
    video_codec: str = "libx264",
    audio_codec: str = "aac",
) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.concat(
        video_files,
        output_file,
        mode="reencode",
        video_codec=video_codec,
        audio_codec=audio_codec,
    )
    return run_plan(engine, plan).succeeded


def get_video_info(video_files: list[str]) -> list[dict]:
    probe = FFprobeRunner()
    return [probe.probe(path) for path in video_files]


def main() -> None:
    inputs = ["clip-1.mp4", "clip-2.mp4"]
    if concatenate_videos_basic(inputs, "joined.mp4"):
        print("Created joined.mp4")


if __name__ == "__main__":
    main()
