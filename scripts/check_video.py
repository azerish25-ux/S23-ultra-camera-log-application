#!/usr/bin/env python3
"""Check S23Log's no-B-frame recordings and decode every frame; not a quality certification."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys


def validate_metadata(data: dict, minimum: float, hlg: bool) -> dict:
    if not math.isfinite(minimum) or minimum < 0:
        raise ValueError("minimum duration must be finite and non-negative")
    streams = data.get("streams", [])
    if len(streams) != 1 or streams[0].get("codec_type") != "video":
        raise ValueError("expected exactly one video stream")
    stream = streams[0]
    if int(stream.get("width", 0)) <= 0 or int(stream.get("height", 0)) <= 0:
        raise ValueError("missing or invalid video dimensions")
    duration = float(data.get("format", {}).get("duration", 0))
    if not math.isfinite(duration) or duration <= 0 or duration < minimum:
        raise ValueError(f"invalid/short duration {duration}s; required {minimum}s")
    packets = data.get("packets", [])
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
    return {"durationSeconds": duration, "packetSpanSeconds": times[-1] - times[0],
            "packets": len(times), "measuredPacketFps": (len(times) - 1) / (times[-1] - times[0]),
            "stream": stream}


def inspect(path: Path, minimum: float, hlg: bool) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"{path}: missing or empty video")
    # Select all video streams so an accidental second track cannot be concealed.
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-show_packets", "-select_streams", "v", "-of", "json", str(path)],
        capture_output=True, text=True, check=True, timeout=120,
    )
    if completed.stderr.strip():
        raise ValueError(f"{path}: ffprobe errors: {completed.stderr.strip()}")
    result = validate_metadata(json.loads(completed.stdout), minimum, hlg)
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
    return {"file": str(path), **result, "fullDecodePassed": True,
            "scope": "metadata, all packet timestamps and full video decode; not thermal or visual-quality certification"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--min-duration", type=float, default=1)
    parser.add_argument("--expect-hlg10", action="store_true")
    args = parser.parse_args()
    if not math.isfinite(args.min_duration) or args.min_duration < 0:
        parser.error("minimum duration must be finite and non-negative")
    paths = sorted(args.path.rglob("*.mp4")) if args.path.is_dir() else [args.path]
    if not paths:
        raise ValueError("No recorded MP4 files found")
    print(json.dumps([inspect(p, args.min_duration, args.expect_hlg10) for p in paths], indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        print(f"Video validation failed: {error}", file=sys.stderr)
        sys.exit(1)
