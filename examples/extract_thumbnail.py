"""Create one or more thumbnails through shared typed plans."""

from __future__ import annotations

from pathlib import Path

from examples._shared import run_plan
from pyffmpegcore import FFprobeRunner, WorkflowEngine


def extract_thumbnail(
    video_path: str,
    output_path: str,
    timestamp: str = "00:00:01",
    width: int = 320,
    height: int | None = None,
) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.thumbnail(
        video_path,
        output_path,
        timestamp=timestamp,
        width=width,
        height=height,
    )
    return run_plan(engine, plan).succeeded


def extract_multiple_thumbnails(
    video_path: str,
    output_dir: str,
    timestamps: list[str],
    width: int = 320,
) -> list[str]:
    outputs = []
    for index, timestamp in enumerate(timestamps, start=1):
        output = str(Path(output_dir) / f"thumbnail_{index:02d}.jpg")
        if extract_thumbnail(video_path, output, timestamp=timestamp, width=width):
            outputs.append(output)
    return outputs


def extract_smart_thumbnails(video_path: str, output_dir: str, count: int = 5, width: int = 320) -> list[str]:
    if count <= 0:
        raise ValueError("count must be positive")
    duration = FFprobeRunner().get_duration(video_path)
    timestamps = [f"{duration * index / (count + 1):.3f}" for index in range(1, count + 1)]
    return extract_multiple_thumbnails(video_path, output_dir, timestamps, width=width)


def main() -> None:
    if extract_thumbnail("input.mp4", "thumbnail.jpg"):
        print("Thumbnail created: thumbnail.jpg")


if __name__ == "__main__":
    main()
