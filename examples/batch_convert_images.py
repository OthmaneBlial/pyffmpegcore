"""Convert individual images or directories through shared plans."""

from __future__ import annotations

from examples._shared import run_plan
from pyffmpegcore import WorkflowBatch, WorkflowEngine


def _counts(batch: WorkflowBatch) -> dict[str, int]:
    return {
        "total": len(batch.items),
        "successful": batch.succeeded_count,
        "failed": batch.failed_count,
    }


def convert_image(
    input_path: str,
    output_path: str,
    quality: int = 85,
    resize: tuple[int, int] | None = None,
) -> bool:
    engine = WorkflowEngine()
    plan = engine.planner.image(input_path, output_path, quality=quality, resize=resize)
    return run_plan(engine, plan).succeeded


def batch_convert_images(
    input_dir: str,
    output_dir: str,
    patterns: list[str] | None = None,
    output_format: str = "jpg",
    quality: int = 85,
    resize: tuple[int, int] | None = None,
    max_workers: int = 1,
) -> dict[str, int]:
    if patterns not in (None, ["*.png", "*.jpg", "*.jpeg", "*.tiff", "*.bmp", "*.gif"]):
        raise ValueError("custom glob patterns are not part of the deterministic image workflow")
    if max_workers != 1:
        print(
            "The stable example executes deterministically in input order; max_workers is reserved for resumable batches."
        )
    engine = WorkflowEngine()
    plan = engine.planner.images(
        "convert",
        input_dir,
        output_dir,
        output_format=output_format,
        quality=quality,
        resize=resize,
    )
    return _counts(run_plan(engine, plan))


def optimize_images_for_web(
    input_dir: str,
    output_dir: str,
    max_width: int = 1920,
    max_height: int = 1080,
    quality: int = 85,
) -> dict[str, int]:
    engine = WorkflowEngine()
    plan = engine.planner.images(
        "optimize",
        input_dir,
        output_dir,
        max_width=max_width,
        max_height=max_height,
        quality=quality,
    )
    return _counts(run_plan(engine, plan))


def convert_to_webp_batch(
    input_dir: str,
    output_dir: str,
    quality: int = 80,
    lossless: bool = False,
) -> dict[str, int]:
    if lossless:
        raise ValueError("lossless WebP is not part of the stable image profile")
    engine = WorkflowEngine()
    plan = engine.planner.images("webp", input_dir, output_dir, quality=quality)
    return _counts(run_plan(engine, plan))


def main() -> None:
    print(batch_convert_images("images", "converted", output_format="jpg"))


if __name__ == "__main__":
    main()
