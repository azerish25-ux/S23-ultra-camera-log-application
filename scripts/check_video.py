#!/usr/bin/env python3
"""Validate selected A/V tracks and fully decode them; packet alignment is not lip-sync proof."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys


def validate_metadata(data: dict, minimum: float, hlg: bool, expected_audio: str = "auto", channels: int | None = None) -> dict:
    if not math.isfinite(minimum) or minimum < 0:
        raise ValueError("minimum duration must be finite and non-negative")
    streams = data.get("streams", [])
    if expected_audio not in {"auto", "on", "off"}:
        raise ValueError("expected_audio must be auto, on or off")
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    if len(video_streams) != 1 or len(audio_streams) > 1 or len(streams) != 1 + len(audio_streams):
        raise ValueError("expected one video stream and at most one audio stream")
    if expected_audio == "on" and not audio_streams:
        raise ValueError("requested audio track is missing")
    if expected_audio == "off" and audio_streams:
        raise ValueError("audio exists in an explicitly video-only recording")
    if channels is not None and (channels not in (1, 2) or not audio_streams):
        raise ValueError("requested mono/stereo channel count needs an audio track")
    stream = video_streams[0]
    if int(stream.get("width", 0)) <= 0 or int(stream.get("height", 0)) <= 0:
        raise ValueError("missing or invalid video dimensions")
    duration = float(data.get("format", {}).get("duration", 0))
    if not math.isfinite(duration) or duration <= 0 or duration < minimum:
        raise ValueError(f"invalid/short duration {duration}s; required {minimum}s")
    all_packets = data.get("packets", [])
    if audio_streams and (any("stream_index" not in p for p in all_packets) or any("index" not in s for s in streams)):
        raise ValueError("multi-track timestamps require explicit stream indices")
    indices = {s.get("index", 0) for s in streams}
    if len(indices) != len(streams) or any(p.get("stream_index", 0) not in indices for p in all_packets):
        raise ValueError("duplicate or unknown stream index")
    packets = [p for p in all_packets if p.get("stream_index", 0) == stream.get("index", 0)]
    if len(packets) < 2 or any("pts_time" not in p for p in packets):
        raise ValueError("insufficient packets or missing presentation timestamps")
    times = [float(p["pts_time"]) for p in packets]
    if any(not math.isfinite(t) for t in times) or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("non-finite or non-monotonic packet timestamps")
    if times[-1] - times[0] < minimum:
        raise ValueError("packet timestamps do not span the required duration")
    if hlg:
        required = {"codec_name": "hevc", "color_space": "bt2020nc", "color_transfer": "arib-std-b67", "color_primaries": "bt2020", "color_range": "tv"}
        for key, expected in required.items():
            if stream.get(key) != expected:
                raise ValueError(f"expected {key}={expected}, got {stream.get(key)}")
        if stream.get("pix_fmt") not in {"yuv420p10le", "p010le"}:
            raise ValueError("pixel format is not 10-bit 4:2:0")
    result = {"durationSeconds": duration, "packetSpanSeconds": times[-1] - times[0],
              "packets": len(times), "measuredPacketFps": (len(times) - 1) / (times[-1] - times[0]),
              "firstVideoPtsSeconds": times[0], "lastVideoPtsSeconds": times[-1],
              "stream": stream, "audioPresent": bool(audio_streams), "physicalLipSyncVerified": False}
    if audio_streams:
        audio = audio_streams[0]
        if audio.get("codec_name") != "aac" or audio.get("profile") != "LC":
            raise ValueError("expected AAC-LC audio")
        rate, actual_channels = int(audio.get("sample_rate", 0)), int(audio.get("channels", 0))
        if rate != 48000 or actual_channels not in (1, 2) or (channels is not None and actual_channels != channels):
            raise ValueError("audio sample rate/channel count differs from selection")
        audio_packets = [p for p in all_packets if p["stream_index"] == audio["index"]]
        if len(audio_packets) < 2 or any("pts_time" not in p for p in audio_packets):
            raise ValueError("missing AAC samples or audio timestamps")
        audio_times = [float(p["pts_time"]) for p in audio_packets]
        if any(not math.isfinite(t) for t in audio_times) or any(b <= a for a, b in zip(audio_times, audio_times[1:])):
            raise ValueError("non-finite or non-monotonic audio timestamps")
        period = 1024 / rate
        gaps = sum(b - a > 1.5 * period for a, b in zip(audio_times, audio_times[1:]))
        audio_last_duration = float(audio_packets[-1].get("duration_time", period))
        video_last_duration = float(packets[-1].get("duration_time", (times[-1] - times[0]) / (len(times) - 1)))
        if any(not math.isfinite(v) or v <= 0 for v in (audio_last_duration, video_last_duration)):
            raise ValueError("invalid packet duration")
        start = audio_times[0] - times[0]
        end = audio_times[-1] + audio_last_duration - times[-1] - video_last_duration
        result.update(audioStream=audio, audioPackets=len(audio_times), audioPacketSpanSeconds=audio_times[-1] - audio_times[0],
                      firstAudioPtsSeconds=audio_times[0], lastAudioPtsSeconds=audio_times[-1], largeAudioIntervals=gaps,
                      avStartOffsetSeconds=start, avEndOffsetSeconds=end,
                      avPacketCoverage="within_250ms" if abs(start) <= .25 and abs(end) <= .25 and gaps == 0 else "warning",
                      packetCoverageIsNotLipSyncProof=True)
    return result


def inspect(path: Path, minimum: float, hlg: bool, expected_audio: str = "auto", channels: int | None = None) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"{path}: missing or empty video")
    # Inspect every stream: an absent, duplicate or unexpected audio track must not be concealed.
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-show_packets", "-of", "json", str(path)],
        capture_output=True, text=True, check=True, timeout=120,
    )
    if completed.stderr.strip():
        raise ValueError(f"{path}: ffprobe errors: {completed.stderr.strip()}")
    result = validate_metadata(json.loads(completed.stdout), minimum, hlg, expected_audio, channels)
    # Keep the source time base: default 1/fps rounding can create duplicate output
    # DTS in the null muxer even when the input packet timestamps are strictly increasing.
    decoded = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-err_detect", "explode", "-threads", "1",
         "-i", str(path), "-map", "0:v:0", "-an", "-fps_mode", "passthrough",
         "-enc_time_base", "demux", "-f", "null", "-"],
        capture_output=True, text=True, check=True, timeout=300,
    )
    if decoded.stderr.strip():
        raise ValueError(f"{path}: decoder errors: {decoded.stderr.strip()}")
    if result["audioPresent"]:
        audio_decoded = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-err_detect", "explode", "-threads", "1",
             "-i", str(path), "-map", "0:a:0", "-vn", "-f", "null", "-"],
            capture_output=True, text=True, check=True, timeout=300,
        )
        if audio_decoded.stderr.strip():
            raise ValueError(f"{path}: audio decoder errors: {audio_decoded.stderr.strip()}")
    digest = hashlib.sha256()
    byte_count = 0
    with path.open("rb") as source:
        for block in iter(lambda: source.read(64 * 1024), b""):
            digest.update(block)
            byte_count += len(block)
    if byte_count == 0:
        raise ValueError("Cannot identify an empty media container")
    return {"file": str(path), **result, "fullDecodePassed": True,
            "mediaIdentity": {"algorithm": "SHA-256", "sha256": digest.hexdigest(), "byteCount": byte_count},
            "audioFullDecodePassed": True if result["audioPresent"] else None,
            "scope": "all tracks/packet timestamps and full video/audio decode; not physical lip-sync, thermal or visual-quality certification"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--min-duration", type=float, default=1)
    parser.add_argument("--expect-hlg10", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--expect-audio", action="store_true")
    group.add_argument("--expect-video-only", action="store_true")
    parser.add_argument("--audio-channels", type=int, choices=(1, 2))
    args = parser.parse_args()
    expected_audio = "on" if args.expect_audio or args.audio_channels else "off" if args.expect_video_only else "auto"
    if args.expect_video_only and args.audio_channels:
        parser.error("--audio-channels conflicts with --expect-video-only")
    if not math.isfinite(args.min_duration) or args.min_duration < 0:
        parser.error("minimum duration must be finite and non-negative")
    paths = sorted(args.path.rglob("*.mp4")) if args.path.is_dir() else [args.path]
    if not paths:
        raise ValueError("No recorded MP4 files found")
    print(json.dumps([inspect(p, args.min_duration, args.expect_hlg10, expected_audio, args.audio_channels) for p in paths], indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        print(f"Video validation failed: {error}", file=sys.stderr)
        sys.exit(1)
