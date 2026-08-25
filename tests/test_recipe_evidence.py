"""Published recipe evidence remains private, internally consistent, and reviewable."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pyffmpegcore.receipt import validate_receipt

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_ROOT = REPO_ROOT / "docs" / "evidence"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_recipe_evidence_matches_receipts_and_contains_no_private_paths():
    index = json.loads((EVIDENCE_ROOT / "recipe-proof-2026-08-25.json").read_text(encoding="utf-8"))
    assert index["schema_version"] == "1.0"
    assert len(index["measurements"]) == 3

    for measurement in index["measurements"]:
        receipt_path = EVIDENCE_ROOT / measurement["receipt"]
        rendered = receipt_path.read_text(encoding="utf-8")
        receipt = json.loads(rendered)
        proof = receipt["items"][0]["proof"]
        assert validate_receipt(receipt) == ()
        assert receipt["items"][0]["result"]["status"] == "succeeded"
        assert measurement["receipt_sha256"] == _sha256(receipt_path)
        assert measurement["input_bytes"] == proof["input_size_bytes"]
        assert measurement["output_bytes"] == proof["output_size_bytes"]
        assert not any(marker in rendered for marker in ("/Users/", "/home/", "/private/", "C:\\Users\\"))


def test_flagship_recipe_commands_match_the_cli_contract():
    podcast = (REPO_ROOT / "docs" / "recipes" / "podcast.md").read_text(encoding="utf-8")
    assert "--bitrate" not in podcast
    assert "--method loudnorm" in podcast
