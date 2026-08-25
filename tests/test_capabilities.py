"""Capability inventory parsing and workflow-rule contracts."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from pyffmpegcore.capabilities import CapabilityInventory, requirements_for


def _ffmpeg_listing(command, **_kwargs):
    option = command[-1]
    outputs = {
        "-encoders": "Encoders:\n V..... libx264 H.264\n A..... aac AAC\n S..... mov_text text\n",
        "-decoders": "Decoders:\n V..... h264 H.264\n A..... aac AAC\n",
        "-filters": "Filters:\n ... scale V->V\n ... subtitles V->V\n ... atempo A->A\n",
        "-muxers": "Muxers:\n E mp4 MP4\n E image2 image sequence\n",
        "-demuxers": "Demuxers:\n D concat concat files\n D mov QuickTime\n",
        "-protocols": "Supported file protocols:\nInput:\n  file\n  http\nOutput:\n  file\n  pipe\n",
        "-hwaccels": "Hardware acceleration methods:\nvideotoolbox\n",
    }
    return subprocess.CompletedProcess(command, 0, outputs[option], "")


@patch("subprocess.run", side_effect=_ffmpeg_listing)
def test_inventory_covers_all_capability_families(_mock_run):
    inventory = CapabilityInventory.inspect("/custom/ffmpeg")

    assert inventory.supports("encoder:libx264")
    assert inventory.supports("decoder:h264")
    assert inventory.supports("filter:subtitles")
    assert inventory.supports("muxer:mp4")
    assert inventory.supports("demuxer:concat")
    assert inventory.supports("input-protocol:http")
    assert inventory.supports("output-protocol:pipe")
    assert inventory.supports("hwaccel:videotoolbox")
    assert inventory.missing(("encoder:aac", "encoder:libopus")) == ("encoder:libopus",)

    payload = inventory.to_dict()
    assert payload["schema_version"] == "1.0"
    assert payload["decoder_count"] == 2
    assert payload["subtitle_support"] == {"text_encoders": ["mov_text"], "burn_filter": True}


def test_workflow_rules_are_deduplicated_and_extensible():
    requirements = requirements_for("compress", ("encoder:libx264", "muxer:mp4"))

    assert requirements == ("encoder:libx264", "encoder:aac", "muxer:mp4")
