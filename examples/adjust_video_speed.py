"""Change video or audio speed through shared typed plans."""

from __future__ import annotations

from examples._shared import run_plan
from pyffmpegcore import FFprobeRunner, WorkflowEngine


def change_video_speed(
    video_file: str,
    output_file: str,
    speed_multiplier: float,
    maintain_audio_pitch: bool = True,
) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.speed(
        "video",
        video_file,
        output_file,
        factor=speed_multiplier,
        preserve_pitch=maintain_audio_pitch,
    )
    return run_plan(engine, plan).succeeded


def create_time_lapse(video_file: str, output_file: str, speed_up_factor: float = 30.0) -> bool:
    return change_video_speed(video_file, output_file, speed_up_factor, maintain_audio_pitch=False)


def create_slow_motion(video_file: str, output_file: str, slow_down_factor: float = 0.5) -> bool:
    return change_video_speed(video_file, output_file, slow_down_factor)


def adjust_audio_tempo(
    audio_file: str,
    output_file: str,
    tempo_multiplier: float,
    maintain_pitch: bool = True,
) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.speed(
        "audio",
        audio_file,
        output_file,
        factor=tempo_multiplier,
        preserve_pitch=maintain_pitch,
    )
    return run_plan(engine, plan).succeeded


def get_video_info(video_file: str) -> dict:
    return FFprobeRunner().probe(video_file)


def main() -> None:
    if change_video_speed("input.mp4", "faster.mp4", 2.0):
        print("Created faster.mp4")


if __name__ == "__main__":
    main()
