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
    for index_name in ("recipe-proof-2026-08-25.json", "recipe-proof-2026-09-19.json"):
        index = json.loads((EVIDENCE_ROOT / index_name).read_text(encoding="utf-8"))
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
            if "target_bytes" in measurement:
                assert measurement["target_bytes"] == proof["target_size_bytes"]
                assert measurement["target_met"] is proof["target_met"]
            if "size_change_percent" in measurement:
                actual = 100 * (measurement["output_bytes"] / measurement["input_bytes"] - 1)
                assert measurement["size_change_percent"] == round(actual, 1)


def test_flagship_recipe_commands_match_the_cli_contract():
    podcast = (REPO_ROOT / "docs" / "recipes" / "podcast.md").read_text(encoding="utf-8")
    preserve = (REPO_ROOT / "docs" / "recipes" / "preserve-streams.md").read_text(encoding="utf-8")
    recipe_index = (REPO_ROOT / "docs" / "recipes" / "index.md").read_text(encoding="utf-8")
    assert "--bitrate" not in podcast
    assert "--method loudnorm" in podcast
    assert "--preserve-all-streams" in preserve
    assert "--video-codec" not in preserve
    assert "superuser.com/questions/1513289" in preserve
    assert "stackoverflow.com/questions/29082422" in recipe_index
