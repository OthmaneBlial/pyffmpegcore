#!/usr/bin/env python3
"""Bounded, reproducible mutation fuzzing of untrusted JSON/TOML documents."""

from __future__ import annotations

import argparse
import json
import random
import tempfile
import traceback
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

from pyffmpegcore.errors import ValidationError
from pyffmpegcore.pipeline import PipelineSpec
from pyffmpegcore.profiles import ProfileRegistry
from pyffmpegcore.receipt import RunReceipt

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = REPO_ROOT / "fuzz" / "corpus"
TARGETS: dict[str, Callable[[Path], object]] = {
    "pipeline": PipelineSpec.read,
    "profile": ProfileRegistry().load_file,
    "receipt": RunReceipt.read,
}
REPLACEMENTS: tuple[Any, ...] = (None, True, False, 0, -1, 1.5, "", "x", [], {}, ["x"], {"x": "y"})
RAW_BYTES = b'{}[],:="\xff\x00\n\r abc123'
MAX_INPUT_BYTES = 8192


def _paths(value: Any, path: tuple[str | int, ...] = ()) -> list[tuple[str | int, ...]]:
    result = [path]
    if isinstance(value, dict):
        for key, child in value.items():
            result.extend(_paths(child, (*path, key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.extend(_paths(child, (*path, index)))
    return result


def _structured_mutation(data: bytes, rng: random.Random) -> bytes:
    document = json.loads(data)
    path = rng.choice(_paths(document))
    replacement = deepcopy(rng.choice(REPLACEMENTS))
    if not path:
        document = replacement
    else:
        parent = document
        for component in path[:-1]:
            parent = parent[component]
        parent[path[-1]] = replacement
    return json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _raw_mutation(data: bytes, rng: random.Random) -> bytes:
    source = bytearray(data)
    position = rng.randrange(len(source) + 1)
    operation = rng.randrange(4)
    if operation == 0 or not source:
        source[position:position] = bytes([rng.choice(RAW_BYTES)])
    elif operation == 1 and position < len(source):
        del source[position]
    elif operation == 2 and position < len(source):
        source[position] = rng.choice(RAW_BYTES)
    else:
        fragment = source[max(0, position - 8) : position + 8]
        source[position:position] = fragment
    return bytes(source[:MAX_INPUT_BYTES])


def _run_case(target: str, data: bytes, suffix: str, path: Path) -> bool:
    path.with_suffix(suffix).write_bytes(data)
    try:
        TARGETS[target](path.with_suffix(suffix))
    except ValidationError:
        return False
    return True


def fuzz(*, seed: int, iterations: int, crash_dir: Path) -> dict[str, int]:
    rng = random.Random(seed)
    counts: dict[str, int] = {}
    with tempfile.TemporaryDirectory(prefix="pyffmpegcore-parser-fuzz-") as temporary:
        work = Path(temporary) / "candidate"
        for target in TARGETS:
            seeds = sorted(path for path in (CORPUS_ROOT / target).iterdir() if path.suffix in {".json", ".toml"})
            if not seeds:
                raise ValueError(f"no corpus seeds for {target}")
            for index in range(-len(seeds), iterations):
                source = seeds[index + len(seeds)] if index < 0 else rng.choice(seeds)
                data = source.read_bytes()
                if index >= 0:
                    if source.suffix == ".json" and rng.randrange(2):
                        try:
                            data = _structured_mutation(data, rng)
                        except (UnicodeError, json.JSONDecodeError):
                            data = _raw_mutation(data, rng)
                    else:
                        data = _raw_mutation(data, rng)
                if len(data) > MAX_INPUT_BYTES:
                    continue
                try:
                    accepted = _run_case(target, data, source.suffix, work)
                    if index < 0 and accepted != source.name.startswith("valid."):
                        raise AssertionError(f"corpus expectation changed: {source}")
                except Exception:
                    crash_dir.mkdir(parents=True, exist_ok=True)
                    case = crash_dir / f"{target}-{seed}-{index}{source.suffix}"
                    case.write_bytes(data)
                    case.with_suffix(case.suffix + ".traceback.txt").write_text(
                        f"target={target}\nseed={seed}\niteration={index}\nsource={source}\n\n{traceback.format_exc()}",
                        encoding="utf-8",
                    )
                    raise RuntimeError(f"parser fuzz crash; replay {case}") from None
            counts[target] = iterations + len(seeds)
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260919)
    parser.add_argument("--iterations", type=int, default=500, help="mutations per parser")
    parser.add_argument("--crash-dir", type=Path, default=Path("fuzz-crashes"))
    parser.add_argument("--replay", type=Path, help="replay one saved input without mutation")
    parser.add_argument("--target", choices=sorted(TARGETS), help="parser to use with --replay")
    args = parser.parse_args(argv)
    if args.replay:
        if args.target is None:
            parser.error("--replay requires --target")
        try:
            TARGETS[args.target](args.replay)
        except ValidationError as exc:
            print(f"rejected: {exc}")
        else:
            print("accepted")
        return 0
    if args.target is not None:
        parser.error("--target requires --replay")
    if not 1 <= args.iterations <= 10000:
        parser.error("iterations must be between 1 and 10000")
    counts = fuzz(seed=args.seed, iterations=args.iterations, crash_dir=args.crash_dir)
    print(json.dumps({"seed": args.seed, "cases": counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
