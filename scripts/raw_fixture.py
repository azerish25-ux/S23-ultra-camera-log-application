#!/usr/bin/env python3
"""Create a labelled synthetic Bayer sequence for software/codec tests, never device evidence."""
import argparse
import json
from pathlib import Path
import struct
import zlib

import numpy as np


def fixture(folder: Path, width: int = 1024, height: int = 32, frames: int = 48, cfa: int = 0):
    folder.mkdir(parents=True, exist_ok=True)
    header = {"schemaVersion": 1, "kind": "continuous-raw", "source": "RAW_SENSOR",
              "device": {"model": "SYNTHETIC_FIXTURE", "fingerprint": "synthetic/no-device"},
              "logicalCamera": "fixture", "physicalCamera": None, "width": width, "height": height,
              "fpsRequested": 24, "secondsRequested": frames / 24, "orientationDegrees": 0,
              "sampleEncoding": "uint16le", "rowBytes": width * 2, "cfa": cfa,
              "physicalCameraCertified": False}
    source = folder / "synthetic.s23raw"
    with source.open("wb") as stream:
        encoded = json.dumps(header).encode()
        stream.write(b"S23RAW01" + struct.pack("<I", len(encoded)) + encoded)
        # Paired columns preserve a neutral Bayer ramp without an 8-bit intermediate.
        row = np.repeat(np.linspace(256, 15000, width // 2).round().astype("<u2"), 2)
        for i in range(frames):
            pixels = np.tile(row, (height, 1)).astype("<u2")
            # A small moving dark patch detects missing, repeated, or reordered frames.
            x = (i * 6) % (width - 4)
            pixels[0:4, x:x + 4] = 256
            payload = pixels.tobytes()
            metadata = json.dumps({"sensorTimestampNs": 1_000_000_000 + round(i * 1e9 / 24),
                                   "frameNumber": i, "iso": 100, "exposureNs": 20_000_000,
                                   "blackLevels": [256.] * 4, "whiteLevel": 16383}).encode()
            lengths = struct.pack("<IQ", len(metadata), len(payload))
            crc = zlib.crc32(payload, zlib.crc32(metadata, zlib.crc32(lengths))) & 0xffffffff
            stream.write(b"FRM1" + lengths + metadata + payload + struct.pack("<I", crc))
    profile = {"schemaVersion": 1, "kind": "raw-colour-profile",
               "source": {"fingerprint": header["device"]["fingerprint"],
                          **{k: header[k] for k in ("logicalCamera", "physicalCamera", "width", "height", "cfa")}},
               "calibration": {"status": "synthetic", "evidence": "Analytic Bayer fixture; no phone measurement", "illuminant": "D65 synthetic"},
               "sceneScale": 4., "bayerWhiteBalance": [1., 1., 1., 1.], "crop": [0, 0, width, height],
               "iso": 100, "exposureNs": 20_000_000,
               "cameraToXyzD65": [[.638008, .214704, .097744], [.291954, .823841, -.115795], [.002798, -.067034, 1.153294]]}
    path = folder / "synthetic-profile.json"
    path.write_text(json.dumps(profile, indent=2) + "\n")
    return source, profile


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    source, _ = fixture(args.folder)
    print(source)
