"""Architecture contracts for the separated CLI layers."""

from __future__ import annotations

import pytest

from pyffmpegcore.cli_parser import build_parser
from pyffmpegcore.cli_planning import build_cli_plan
from pyffmpegcore.cli_validation import validate_global_contract
from pyffmpegcore.pipeline import PipelineCompiler, PipelineSpec


def test_parser_registers_handler_names_without_importing_handlers():
    args = build_parser().parse_args(["doctor"])

    assert args.handler_name == "handle_doctor"
    assert not hasattr(args, "handler")


def test_global_validation_reports_preview_mode():
    args = build_parser().parse_args(["convert", "--input", "in.mp4", "--output", "out.mp4", "--dry-run"])

    assert validate_global_contract(args, {"convert"}) is True


@pytest.mark.parametrize(
    ("arguments", "step_kind"),
    [
        (["convert", "--input", "{input}", "--output", "{output}"], "workflow"),
        (
            ["profile", "run", "web/mp4-compatible", "--input", "{input}", "--output", "{output}"],
            "profile",
        ),
    ],
)
def test_cli_and_pipeline_compile_the_same_normalized_plan(tmp_path, arguments, step_kind):
    """The two input adapters must converge on the public typed plan contract."""
    input_path = str(tmp_path / "input.mov")
    output_path = str(tmp_path / "output.mp4")
    cli_arguments = [part.format(input=input_path, output=output_path) for part in arguments]
    cli_plan = build_cli_plan(build_parser().parse_args(cli_arguments))
    step = {"id": "video", step_kind: "convert" if step_kind == "workflow" else "web/mp4-compatible"}
    step.update({"input": input_path, "output": output_path})
    spec = PipelineSpec.from_dict({"schema_version": "1.0", "name": "same_job", "steps": [step]}, base_dir=tmp_path)
    pipeline_plan = PipelineCompiler().compile(spec).steps[0].plan

    assert cli_plan.to_dict() == pipeline_plan.to_dict()
    assert cli_plan.to_dict()["schema_version"] == "1.0"
