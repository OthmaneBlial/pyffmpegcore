"""Normalize speech or create a mastered track through shared plans."""

from __future__ import annotations

from pathlib import Path

from examples._shared import run_plan
from pyffmpegcore import FFprobeRunner, WorkflowEngine


def normalize_audio_loudnorm(
    audio_file: str,
    output_file: str,
    target_i: float = -16.0,
    target_tp: float = -1.5,
    target_lra: float = 11.0,
) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.normalize_audio(
        audio_file,
        output_file,
        method="loudnorm",
        target_i=target_i,
        target_tp=target_tp,
        target_lra=target_lra,
    )
    return run_plan(engine, plan).succeeded


def create_mastered_audio(audio_file: str, output_file: str) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.normalize_audio(audio_file, output_file, method="master")
    return run_plan(engine, plan).succeeded


def analyze_audio_levels(audio_file: str) -> dict:
    return FFprobeRunner().probe(audio_file)


def batch_normalize_audio(audio_dir: str, output_dir: str) -> dict[str, int]:
    inputs = sorted(path for path in Path(audio_dir).iterdir() if path.suffix.lower() in {".mp3", ".wav", ".m4a"})
    successful = 0
    for source in inputs:
        if normalize_audio_loudnorm(str(source), str(Path(output_dir) / f"{source.stem}.mp3")):
            successful += 1
    return {"total": len(inputs), "successful": successful, "failed": len(inputs) - successful}


def main() -> None:
    if normalize_audio_loudnorm("input.wav", "normalized.mp3"):
        print("Created normalized.mp3")


if __name__ == "__main__":
    main()
