"""Compress a video while consuming typed FFmpeg progress events."""

from examples._shared import print_progress, run_plan
from pyffmpegcore import CompressOptions, WorkflowEngine


def main() -> None:
    engine = WorkflowEngine()
    plan = engine.planner.compress(
        "input.mp4",
        "compressed.mp4",
        CompressOptions(crf=28, two_pass=False),
    )
    batch = run_plan(engine, plan, progress_callback=print_progress)
    print("Compression successful!" if batch.succeeded else "Compression failed!")


if __name__ == "__main__":
    main()
