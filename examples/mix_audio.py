"""Mix, join, crossfade, or layer audio through shared plans."""

from __future__ import annotations

from examples._shared import run_plan
from pyffmpegcore import FFprobeRunner, WorkflowEngine


def mix_audio_files(audio_files: list[str], output_file: str, volumes: list[float] | None = None) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.mix_audio("mix", audio_files, output_file, volumes=volumes)
    return run_plan(engine, plan).succeeded


def merge_audio_sequentially(audio_files: list[str], output_file: str) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.mix_audio("concat", audio_files, output_file)
    return run_plan(engine, plan).succeeded


def create_audio_mashup(
    audio_files: list[str],
    output_file: str,
    crossfade_duration: float = 2.0,
) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.mix_audio(
        "mashup",
        audio_files,
        output_file,
        crossfade_duration=crossfade_duration,
    )
    return run_plan(engine, plan).succeeded


def add_background_music(
    main_audio: str,
    background_audio: str,
    output_file: str,
    bg_volume: float = 0.3,
) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.mix_audio(
        "background",
        [main_audio, background_audio],
        output_file,
        background_volume=bg_volume,
    )
    return run_plan(engine, plan).succeeded


def get_audio_info(audio_files: list[str]) -> list[dict]:
    probe = FFprobeRunner()
    return [probe.probe(path) for path in audio_files]


def main() -> None:
    if mix_audio_files(["voice.wav", "music.mp3"], "mixed.mp3", volumes=[1.0, 0.25]):
        print("Created mixed.mp3")


if __name__ == "__main__":
    main()
