#!/usr/bin/env python3
"""Independent ffprobe acceptance check for recorded files; does not certify image quality."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def inspect(path: Path, minimum: float, hlg: bool) -> dict:
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-show_packets", "-select_streams", "v:0", "-of", "json", str(path)],
        capture_output=True, text=True, check=True, timeout=120,
    )
    data = json.loads(completed.stdout)
    streams = data.get("streams", [])
    if len(streams) != 1:
        raise ValueError(f"{path}: expected one selected video stream")
    stream = streams[0]
    duration = float(data.get("format", {}).get("duration", 0))
    if duration < minimum:
        raise ValueError(f"{path}: {duration}s is shorter than required {minimum}s")
    packets = data.get("packets", [])
    times = [float(p["pts_time"]) for p in packets if "pts_time" in p]
    if len(times) < 2 or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError(f"{path}: insufficient or non-monotonic packet timestamps")
    if hlg:
        required = {"codec_name": "hevc", "color_space": "bt2020nc", "color_transfer": "arib-std-b67", "color_primaries": "bt2020", "color_range": "tv"}
        for key, expected in required.items():
            if stream.get(key) != expected:
                raise ValueError(f"{path}: expected {key}={expected}, got {stream.get(key)}")
        if stream.get("pix_fmt") not in {"yuv420p10le", "p010le"}:
            raise ValueError(f"{path}: decoded pixel format is not 10-bit 4:2:0")
    return {"file": str(path), "durationSeconds": duration, "packets": len(times),
            "measuredPacketFps": (len(times) - 1) / (times[-1] - times[0]), "stream": stream,
            "scope": "bitstream metadata and packet timing, not thermal or visual-quality certification"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--min-duration", type=float, default=1)
    parser.add_argument("--expect-hlg10", action="store_true")
    args = parser.parse_args()
    if args.min_duration < 0:
        parser.error("minimum duration must be non-negative")
    paths = sorted(args.path.rglob("*.mp4")) if args.path.is_dir() else [args.path]
    if not paths:
        raise ValueError("No recorded MP4 files found")
    print(json.dumps([inspect(p, args.min_duration, args.expect_hlg10) for p in paths], indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Video validation failed: {error}", file=sys.stderr)
        sys.exit(1)
