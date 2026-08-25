"""Human and JSON presentation for plans and preflight reports."""

from __future__ import annotations

import json
import shlex

from .domain import ExecutionPlan
from .preflight import PreflightReport


def safe_command_display(command: tuple[str, ...]) -> str:
    """Quote an argument vector for display only; callers never execute this string."""
    return shlex.join(command)


def plan_payload(plan: ExecutionPlan, preflight: PreflightReport) -> dict[str, object]:
    """Return the versioned machine-readable preview document."""
    return {
        "schema_version": "1.0",
        "plan": plan.to_dict(),
        "preflight": preflight.to_dict(),
    }


def render_plan_json(plan: ExecutionPlan, preflight: PreflightReport) -> str:
    return json.dumps(plan_payload(plan, preflight), indent=2)


def render_plan_text(plan: ExecutionPlan, preflight: PreflightReport, *, explain: bool) -> str:
    """Explain the same immutable plan facts shown in JSON."""
    lines = [
        f"Plan {plan.schema_version} — {plan.workflow}",
        f"Overwrite policy: {plan.policy.overwrite.value}",
        f"Timeout: {plan.policy.timeout_seconds if plan.policy.timeout_seconds is not None else 'none'}",
        "Inputs:",
        *[f"  {value}" for value in plan.inputs],
        "Expected outputs:",
        *[f"  {value}" for value in plan.outputs],
        "Argument vectors (display only; no shell is used):",
    ]
    for index, step in enumerate(plan.execution_steps, 1):
        lines.append(f"  {index}. {step.name}: {safe_command_display(step.command)}")
    if explain:
        lines.extend(["Selected streams:", *[f"  {value}" for value in plan.selected_streams]])
        lines.extend(["Operations and trade-offs:", *[f"  {value}" for value in plan.operations]])
        lines.extend(["Required capabilities:", *[f"  {value}" for value in plan.required_capabilities]])
        if plan.warnings:
            lines.extend(["Warnings:", *[f"  {value}" for value in plan.warnings]])
    lines.extend(["", preflight.render()])
    return "\n".join(lines)
