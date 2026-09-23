"""Human-readable probe report contracts."""

from __future__ import annotations

from pyffmpegcore.cli import main


def test_human_probe_reports_every_stream_and_video_decision_facts(tmp_path, capsys, monkeypatch):
    media_path = tmp_path / "source.mkv"
    media_path.touch()
    metadata = {
        "filename": str(media_path),
        "format_name": "matroska",
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "hevc",
                "width": 3840,
                "height": 2160,
                "rotation": 90.0,
                "color": {
                    "color_space": "bt2020nc",
                    "color_transfer": "smpte2084",
                    "color_primaries": "bt2020",
                },
                "details": {"pix_fmt": "yuv420p10le", "avg_frame_rate": "25/1", "r_frame_rate": "30/1"},
            },
            {"index": 1, "codec_type": "audio", "codec_name": "aac", "sample_rate": 48000, "channels": 2},
            {"index": 2, "codec_type": "audio", "codec_name": "ac3", "language": "fra", "channels": 6},
            {"index": 3, "codec_type": "subtitle", "codec_name": "subrip", "language": "fra"},
            {"index": 4, "codec_type": "attachment", "codec_name": "ttf", "tags": {"filename": "font.ttf"}},
        ],
    }
    monkeypatch.setattr("pyffmpegcore.cli.FFprobeRunner.probe", lambda _self, _path: metadata)

    assert main(["probe", "--input", str(media_path)]) == 0
    output = capsys.readouterr().out

    assert "Video stream:" in output
    assert "Display rotation metadata: 90°" in output
    assert "Pixel format: yuv420p10le" in output
    assert "Frame rates: average 25/1 fps; nominal 30/1 fps" in output
    assert "may indicate variable frame rate" in output
    assert "color_transfer=smpte2084" in output
    assert "Audio stream 2:" in output
    assert "Subtitle stream:" in output
    assert "Language: fra" in output
    assert "Attachment stream:" in output
    assert "Filename: font.ttf" in output
