#!/usr/bin/env python3
"""Copy emulator evidence with bounded ADB retries; never accept a partial transfer."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile


def pull_videos(destination: Path, attempts: int = 3) -> None:
    if not 1 <= attempts <= 3:
        raise ValueError("Transfer attempts must be between one and three")
    if destination.exists():
        raise ValueError(f"Refusing to replace existing evidence: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, attempts + 1):
        # Every retry starts in a new host directory, not a mixture of partial copies.
        with tempfile.TemporaryDirectory(prefix="s23log-transfer-", dir=destination.parent) as temporary:
            staged = Path(temporary) / "videos"
            try:
                subprocess.run(["adb", "wait-for-device"], check=True, timeout=20, capture_output=True, text=True)
                result = subprocess.run(
                    ["adb", "pull", "/sdcard/Movies/S23Log", str(staged)],
                    check=True, timeout=60, capture_output=True, text=True,
                )
                clips = list(staged.rglob("*.mp4"))
                if not staged.is_dir() or not clips or any(p.stat().st_size == 0 for p in clips):
                    raise ValueError("ADB reported success without a nonempty video transfer")
                staged.rename(destination)
                print(result.stdout, end="")
                print(f"Copied {len(clips)} videos on transfer attempt {attempt}; content validation follows.")
                return
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                print(f"ADB evidence transfer {attempt}/{attempts} failed: {error}", file=sys.stderr)
                if isinstance(error, subprocess.CalledProcessError) and error.stderr:
                    print(error.stderr, file=sys.stderr)
                if attempt == attempts:
                    raise RuntimeError("Could not obtain a complete video transfer; acceptance has not passed") from error
                try:
                    subprocess.run(["adb", "reconnect", "offline"], check=True, timeout=10, capture_output=True, text=True)
                except (OSError, subprocess.SubprocessError) as reconnect_error:
                    print(f"Reconnect not yet complete: {reconnect_error}", file=sys.stderr)
    raise AssertionError("Transfer loop did not produce a result")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        pull_videos(args.destination)
    except (OSError, ValueError, RuntimeError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
