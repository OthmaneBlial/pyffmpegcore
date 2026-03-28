#!/usr/bin/env python3
"""
Example: Adjust video and audio speed/tempo.

This example demonstrates how to change playback speed for videos and audio
using the existing FFmpeg runner.
"""

from __future__ import annotations

import os
from typing import Dict, Optional

from pyffmpegcore import FFmpegRunner, FFprobeRunner


def _build_atempo_chain(speed_factor: float) -> str:
    """
    Build an atempo filter chain for any positive speed factor.
    """
    if speed_factor <= 0:
        raise ValueError("speed_factor must be positive")

    if 0.5 <= speed_factor <= 2.0:
        return f"atempo={speed_factor}"

    factors = []
    current = speed_factor

    while current > 2.0:
        factors.append(2.0)
        current /= 2.0

    while current < 0.5:
        factors.append(0.5)
        current /= 0.5

    if current != 1.0:
        factors.append(current)

    return ",".join(f"atempo={factor}" for factor in factors)


def _probe_media(input_file: str) -> Optional[Dict[str, object]]:
    try:
        return FFprobeRunner().probe(input_file)
    except Exception as exc:
        print(f"Could not probe {input_file}: {exc}")
        return None


def change_video_speed(
    video_file: str,
    output_file: str,
    speed_multiplier: float,
    maintain_audio_pitch: bool = True,
) -> bool:
    """
    Change the playback speed of a video.
    """
    if speed_multiplier <= 0:
        print("Speed multiplier must be positive")
        return False

    metadata = _probe_media(video_file)
    if metadata is None:
        return False

    has_audio = bool(metadata.get("audio"))
    runner = FFmpegRunner()

    args = ["-i", video_file]

    if has_audio:
        if maintain_audio_pitch:
            audio_filter = _build_atempo_chain(speed_multiplier)
        else:
            sample_rate = metadata.get("audio", {}).get("sample_rate", 44100)
            audio_filter = f"asetrate={sample_rate}*{speed_multiplier},aresample={sample_rate}"

        filter_complex = (
            f"[0:v]setpts=(PTS-STARTPTS)/{speed_multiplier}[v];"
            f"[0:a]{audio_filter}[a]"
        )
        args.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[v]",
                "-map",
                "[a]",
            ]
        )
    else:
        args.extend(["-vf", f"setpts=(PTS-STARTPTS)/{speed_multiplier}"])

    args.extend(["-c:v", "libx264"])
    if has_audio:
        args.extend(["-c:a", "aac"])
    args.extend(["-y", output_file])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Video speed adjusted ({speed_multiplier}x): {output_file}")
        return True

    print(f"Failed to adjust video speed: {result.stderr}")
    return False


def create_time_lapse(video_file: str, output_file: str, speed_up_factor: float = 30.0) -> bool:
    """
    Create a time-lapse style output by increasing playback speed.
    """
    return change_video_speed(
        video_file,
        output_file,
        speed_up_factor,
        maintain_audio_pitch=False,
    )


def create_slow_motion(video_file: str, output_file: str, slow_down_factor: float = 0.5) -> bool:
    """
    Create a slow-motion style output by decreasing playback speed.
    """
    return change_video_speed(
        video_file,
        output_file,
        slow_down_factor,
        maintain_audio_pitch=True,
    )


def adjust_audio_tempo(
    audio_file: str,
    output_file: str,
    tempo_multiplier: float,
    maintain_pitch: bool = True,
) -> bool:
    """
    Adjust the tempo of an audio file.
    """
    if tempo_multiplier <= 0:
        print("Tempo multiplier must be positive")
        return False

    metadata = _probe_media(audio_file)
    if metadata is None:
        return False

    runner = FFmpegRunner()
    args = ["-i", audio_file]

    if maintain_pitch:
        args.extend(["-filter:a", _build_atempo_chain(tempo_multiplier)])
    else:
        sample_rate = metadata.get("audio", {}).get("sample_rate", 44100)
        args.extend(
            [
                "-filter:a",
                f"asetrate={sample_rate}*{tempo_multiplier},aresample={sample_rate}",
            ]
        )

    args.extend(["-c:a", "aac", "-b:a", "192k", "-y", output_file])

    result = runner.run(args)

    if result.returncode == 0:
        print(f"Audio tempo adjusted ({tempo_multiplier}x): {output_file}")
        return True

    print(f"Failed to adjust audio tempo: {result.stderr}")
    return False


def create_video_summary(
    video_file: str,
    output_file: str,
    segment_duration: float = 5.0,
    speed_multiplier: float = 2.0,
) -> bool:
    """
    Create a highlight-style summary by sampling segments across the source.
    """
    if segment_duration <= 0 or speed_multiplier <= 0:
        print("segment_duration and speed_multiplier must be positive")
        return False

    metadata = _probe_media(video_file)
    if metadata is None:
        return False

    duration = float(metadata.get("duration", 0) or 0)
    has_audio = bool(metadata.get("audio"))
    if duration <= segment_duration:
        print("Video is too short for summary creation")
        return False

    segment_count = min(6, max(2, int(duration // segment_duration)))
    interval = max(segment_duration, duration / (segment_count + 1))
    segments = []

    for index in range(segment_count):
        start = min(index * interval, max(0.0, duration - segment_duration))
        end = min(duration, start + segment_duration)
        if end > start:
            segments.append((start, end))

    if not segments:
        print("No valid segments were selected for summary creation")
        return False

    args = ["-i", video_file]
    filter_parts = []

    for index, (start, end) in enumerate(segments):
        filter_parts.append(
            f"[0:v]trim=start={start}:end={end},setpts=(PTS-STARTPTS)/{speed_multiplier}[v{index}]"
        )
        if has_audio:
            filter_parts.append(
                f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS,{_build_atempo_chain(speed_multiplier)}[a{index}]"
            )

    video_inputs = "".join(f"[v{index}]" for index in range(len(segments)))
    filter_parts.append(f"{video_inputs}concat=n={len(segments)}:v=1:a=0[vout]")

    if has_audio:
        audio_inputs = "".join(f"[a{index}]" for index in range(len(segments)))
        filter_parts.append(f"{audio_inputs}concat=n={len(segments)}:v=0:a=1[aout]")

    args.extend(["-filter_complex", ";".join(filter_parts), "-map", "[vout]"])
    if has_audio:
        args.extend(["-map", "[aout]"])

    args.extend(["-c:v", "libx264"])
    if has_audio:
        args.extend(["-c:a", "aac"])
    args.extend(["-y", output_file])

    result = FFmpegRunner().run(args)

    if result.returncode == 0:
        print(f"Video summary created: {output_file}")
        return True

    print(f"Failed to create video summary: {result.stderr}")
    return False


def reverse_video(video_file: str, output_file: str) -> bool:
    """
    Reverse a video, including audio when available.
    """
    metadata = _probe_media(video_file)
    if metadata is None:
        return False

    has_audio = bool(metadata.get("audio"))
    args = ["-i", video_file]

    if has_audio:
        args.extend(
            [
                "-filter_complex",
                "[0:v]reverse[rvid];[0:a]areverse[raud]",
                "-map",
                "[rvid]",
                "-map",
                "[raud]",
            ]
        )
    else:
        args.extend(["-vf", "reverse"])

    args.extend(["-c:v", "libx264"])
    if has_audio:
        args.extend(["-c:a", "aac"])
    args.extend(["-y", output_file])

    result = FFmpegRunner().run(args)

    if result.returncode == 0:
        print(f"Video reversed: {output_file}")
        return True

    print(f"Failed to reverse video: {result.stderr}")
    return False


def get_video_info(video_file: str) -> dict:
    """
    Get a simplified summary for a media file.
    """
    metadata = _probe_media(video_file)
    if metadata is None:
        return {}

    video = metadata.get("video", {})
    audio = metadata.get("audio", {})

    return {
        "duration": metadata.get("duration", 0),
        "width": video.get("width", 0),
        "height": video.get("height", 0),
        "video_codec": video.get("codec", "unknown"),
        "audio_codec": audio.get("codec", "unknown"),
        "has_audio": bool(audio),
    }


def main() -> None:
    """
    Demonstrate speed and tempo adjustments on local sample media.
    """
    video_file = "sample.mp4"
    audio_file = "sample.mp3"

    if not os.path.exists(video_file):
        print(f"Example video file '{video_file}' not found.")
        print("This example shows the API usage for speed adjustment.")
        return

    print("=== Video Information ===")
    info = get_video_info(video_file)
    if info:
        print(f"Duration: {info['duration']:.1f}s")
        print(f"Resolution: {info['width']}x{info['height']}")
        print(f"Video codec: {info['video_codec']}")
        print(f"Audio codec: {info['audio_codec']}")

    print("\n=== Speed Up Video (2x) ===")
    change_video_speed(video_file, "sped_up_2x.mp4", 2.0, maintain_audio_pitch=True)

    print("\n=== Slow Down Video (0.5x) ===")
    create_slow_motion(video_file, "slow_motion.mp4", 0.5)

    print("\n=== Time-Lapse Style Output (10x) ===")
    create_time_lapse(video_file, "timelapse.mp4", 10.0)

    print("\n=== Reverse Video ===")
    reverse_video(video_file, "reversed.mp4")

    print("\n=== Video Summary ===")
    create_video_summary(video_file, "summary.mp4", segment_duration=3.0, speed_multiplier=2.0)

    if os.path.exists(audio_file):
        print("\n=== Adjust Audio Tempo ===")
        adjust_audio_tempo(audio_file, "tempo_up.mp3", 1.5, maintain_pitch=True)
        adjust_audio_tempo(audio_file, "tempo_down.mp3", 0.8, maintain_pitch=True)
    else:
        print(f"\nAudio file '{audio_file}' not found - skipping audio tempo examples")

    print("\nSpeed adjustment examples completed!")
    print(
        "Output files: sped_up_2x.mp4, slow_motion.mp4, timelapse.mp4, "
        "reversed.mp4, summary.mp4, tempo_up.mp3, tempo_down.mp3"
    )


if __name__ == "__main__":
    main()
