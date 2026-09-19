"""The saved parser corpus must remain replayable before CI mutation fuzzing."""

from __future__ import annotations

from pathlib import Path

from scripts.fuzz_parsers import fuzz


def test_parser_fuzz_replays_valid_invalid_seeds_and_mutations(tmp_path: Path) -> None:
    crashes = tmp_path / "crashes"
    counts = fuzz(seed=20260919, iterations=12, crash_dir=crashes)
    assert counts == {"pipeline": 15, "profile": 15, "receipt": 15}
    assert not crashes.exists()
