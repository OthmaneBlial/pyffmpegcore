#!/usr/bin/env python3
"""Validate and evaluate the workflow capability catalog for this FFmpeg build."""

from __future__ import annotations

import argparse
import json

from pyffmpegcore.capabilities import CapabilityInventory, capability_rule_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg-path", default="ffmpeg")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = capability_rule_report(CapabilityInventory.inspect(args.ffmpeg_path))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Capability catalog {'PASS' if report['catalog_valid'] else 'FAIL'}")
        for workflow, facts in report["workflows"].items():
            missing = ", ".join(facts["missing"]) or "none"
            print(f"{workflow}: missing={missing}")
    return 0 if report["catalog_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
