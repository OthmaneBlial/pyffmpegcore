#!/usr/bin/env python3
"""Turn the six exact-wheel CI compatibility artifacts into a readable report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_CELLS = {(system, python) for system in ("Linux", "macOS", "Windows") for python in ("3.10", "3.14")}


def check_passed(command: dict[str, object]) -> bool:
    """Accept an expected refusal only when the installer validated its remedy."""
    if "expected_returncode" in command:
        return command.get("passed") is True and command["returncode"] == command["expected_returncode"]
    return command["returncode"] == 0 and command.get("passed", True) is True


def load_cell(directory: Path) -> dict[str, str | int]:
    report = json.loads((directory / "compatibility-report.json").read_text(encoding="utf-8"))
    catalog = json.loads((directory / "capability-catalog-report.json").read_text(encoding="utf-8"))
    commands = report["commands"]
    failures = [command["name"] for command in commands if not check_passed(command)]
    if failures or not catalog["catalog_valid"]:
        raise ValueError(f"{directory.name}: failed checks: {failures or catalog['catalog_errors']}")
    doctor = next(command for command in commands if command["name"] == "cli-doctor")
    facts = json.loads(doctor["stdout"])
    system = facts["platform"]["system"]
    if system == "Darwin":
        system = "macOS"
    python = ".".join(facts["python"]["version"].split(".")[:2])
    if (system, python) not in EXPECTED_CELLS:
        raise ValueError(f"{directory.name}: unexpected OS/Python cell {system} {python}")
    missing = sorted(
        f"{name}: {', '.join(workflow['missing'])}"
        for name, workflow in catalog["workflows"].items()
        if workflow["missing"]
    )
    return {
        "system": system,
        "python": facts["python"]["version"],
        "architecture": facts["platform"]["machine"],
        "ffmpeg": facts["ffmpeg"]["version"].split(" Copyright", maxsplit=1)[0],
        "checks": len(commands),
        "wheel": report["artifact"]["sha256"],
        "missing": "; ".join(missing) or "none",
    }


def render_report(root: Path, run_url: str) -> str:
    cells = [load_cell(directory) for directory in sorted(root.glob("compatibility-*/"))]
    found = {(str(cell["system"]), ".".join(str(cell["python"]).split(".")[:2])) for cell in cells}
    if found != EXPECTED_CELLS or len(cells) != len(EXPECTED_CELLS):
        raise ValueError(f"Expected six OS/Python cells; found {sorted(found)}")
    wheels = {cell["wheel"] for cell in cells}
    if len(wheels) != 1:
        raise ValueError("Compatibility cells did not install the same wheel")
    lines = [
        "# Exact-wheel compatibility evidence",
        "",
        f"CI run: {run_url}",
        f"Wheel SHA-256: `{wheels.pop()}`",
        "",
        "| OS | Architecture | Python | FFmpeg | Passed checks | Catalog gaps on this build |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for cell in sorted(cells, key=lambda item: (str(item["system"]), str(item["python"]))):
        lines.append(
            f"| {cell['system']} | {cell['architecture']} | {cell['python']} | "
            f"{cell['ffmpeg']} | {cell['checks']}/{cell['checks']} | {cell['missing']} |"
        )
    lines.extend(
        [
            "",
            "The checks install one prebuilt wheel, then exercise the quickstart, "
            "probe, conversion, stream preservation, audio extraction, thumbnails, "
            "five profiles, batch, pipeline, and four expected error remedies. "
            "A catalog gap means that optional "
            "capability is unavailable on this FFmpeg build; it is not a passed "
            "media test for that capability.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", type=Path, help="directory containing six compatibility-* folders")
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = render_report(args.artifacts, args.run_url)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
