"""Render waveform images through the public workflow engine."""

from __future__ import annotations

from examples._shared import run_plan
from pyffmpegcore import WorkflowEngine


def generate_waveform_image(
    audio_path: str,
    output_path: str,
    width: int = 1200,
    height: int = 300,
    colors: str = "white",
) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.waveform(audio_path, output_path, width=width, height=height, colors=colors)
    return run_plan(engine, plan).succeeded


def generate_detailed_waveform(
    audio_path: str,
    output_path: str,
    width: int = 1200,
    height: int = 300,
) -> bool:
    """Render a high-contrast waveform using the same supported workflow."""
    return generate_waveform_image(audio_path, output_path, width=width, height=height, colors="green|red")


def main() -> None:
    if generate_waveform_image("input.mp3", "waveform.png"):
        print("Waveform created: waveform.png")


if __name__ == "__main__":
    main()
