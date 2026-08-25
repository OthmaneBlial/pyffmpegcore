"""Convert a video through the public typed workflow engine."""

from examples._shared import run_plan
from pyffmpegcore import ConvertOptions, WorkflowEngine


def main() -> None:
    engine = WorkflowEngine()
    plan = engine.planner.convert(
        "input.avi",
        "output.mp4",
        ConvertOptions(video_codec="libx264", audio_codec="aac"),
    )
    batch = run_plan(engine, plan)
    print("Conversion successful!" if batch.succeeded else "Conversion failed!")


if __name__ == "__main__":
    main()
