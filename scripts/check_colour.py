#!/usr/bin/env python3
"""Check pixel evidence; keep unavailable HDR hardware separate from passed GPU arithmetic."""
import argparse
import array
import json
import math
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile

from check_video import inspect as inspect_video

ROOT = "files/exports/colour/"


def number(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Invalid {name}")
    return float(value)


def check_gpu(data: dict) -> dict:
    if data.get("kind") != "colour-gpu" or data.get("status") != "passed":
        raise ValueError("Missing executed colour GPU tests")
    p = data.get("probe", {})
    good, bad = p.get("fp16ToRgb10", {}), p.get("negative8Bit", {})
    if p.get("status") != "passed" or p.get("monitorIndependent") is not True:
        raise ValueError("Missing independent monitor pixel evidence")
    if good.get("passed") is not True or bad.get("passed") is not False:
        raise ValueError("Missing precision pass and rejected 8-bit negative control")
    if (number(good.get("distinctLevels"), "ramp levels") < 768 or
            number(good.get("maximumError"), "ramp error") > 1.25 / 1023 or
            good.get("monotonic") is not True):
        raise ValueError("Precision measurements do not satisfy the ramp contract")
    if number(p.get("referenceLogMaximumError"), "reference error") >= .002:
        raise ValueError("Reference Log arithmetic failed")
    if number(data.get("bt2020PatchMaximumError"), "YUV patch error") >= .003:
        raise ValueError("BT.2020 range/matrix test failed")
    if number(data.get("monitorMaximumError"), "monitor error") >= .002:
        raise ValueError("Monitor arithmetic failed")
    if data.get("physicalCameraCertified") is not False or data.get("cameraYuvImportTested") is not False:
        raise ValueError("Synthetic pixel results must not certify the camera import")
    return p


def check_gate(data: dict, kind: str, success: str) -> str:
    if data.get("kind") != kind:
        raise ValueError(f"Missing {kind} gate")
    state = data.get("status")
    if state == "unavailable":
        if not isinstance(data.get("reason"), str) or not data["reason"].strip():
            raise ValueError("Unavailable hardware needs a reason")
    elif state != success:
        raise ValueError(f"Unexpected {kind} result: {state}")
    return state


def measure_luma(values: list[int], width: int, height: int) -> dict:
    """Lossy encoder identity check, NOT proof of effective bit depth in arbitrary camera images."""
    if width != 1024 or height != 128 or len(values) != width * height:
        raise ValueError("Wrong encoded-ramp dimensions")
    if any(isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 1023 for v in values):
        raise ValueError("Invalid 10-bit luma code")
    # Ignore chroma and average rows away from edges; no scaling or tone mapping is allowed.
    rows = range(16, height - 16)
    means = [sum(values[y * width + x] for y in rows) / len(rows) for x in range(width)]
    errors = [abs(value - (64 + 876 * x / 1023)) for x, value in enumerate(means)]
    mae, maximum = sum(errors) / width, max(errors)
    if mae > 3 or maximum > 12 or abs(means[0] - 64) > 8 or abs(means[-1] - 940) > 8:
        raise ValueError(f"Encoded HLG identity/range failed: mean={mae:.3f}, max={maximum:.3f}")
    return {"passed": True, "meanAbsoluteLumaCodeError": mae, "maximumLumaCodeError": maximum,
            "blackCode": means[0], "whiteCode": means[-1], "meanErrorLimitCodes": 3,
            "maximumErrorLimitCodes": 12, "scope": "Decoded neutral ramp through a lossy encoder; not camera precision certification"}


def check_timing_manifest(manifest: dict) -> None:
    fixtures = manifest.get("fixtures", [])
    if len(fixtures) != 2 or {f.get("fps") for f in fixtures} != {24, 30}:
        raise ValueError("Missing processed 24/30 fps fixtures")
    if any(f.get("colourProcessor") != "production_RGBA16F_HLG_identity" or
           f.get("monitorChangedDuringFixture") is not True for f in fixtures):
        raise ValueError("Timing fixtures did not exercise the colour stage and monitor switches")


def verify_archive(path: Path) -> dict:
    files = {}
    with tarfile.open(path, "r:*") as tar:
        for item in tar.getmembers():
            name = PurePosixPath(item.name)
            if name.is_absolute() or ".." in name.parts or item.issym() or item.islnk():
                raise ValueError("Unsafe colour evidence archive")
            if not item.isfile():
                continue
            key = str(name)
            if not (key.startswith(ROOT) or key == "files/exports/timing-fixtures/manifest.json"):
                continue
            if key in files or not 0 < item.size <= 32 * 1024 * 1024:
                raise ValueError("Duplicated or invalid-size colour evidence")
            files[key] = tar.extractfile(item).read()
    def read(name):
        if name not in files:
            raise ValueError(f"Missing colour evidence: {name}")
        return json.loads(files[name])
    gpu, encoder, camera = (read(ROOT + name + ".json") for name in ("gpu", "encoder", "camera"))
    probe = check_gpu(gpu)
    es = check_gate(encoder, "colour-encoder", "encoded")
    cs = check_gate(camera, "colour-camera", "recorded")
    manifest = read("files/exports/timing-fixtures/manifest.json")
    check_timing_manifest(manifest)
    revisions = [d.get("appCommit") for d in (gpu, encoder, camera, manifest)]
    if not revisions[0] or any(r != revisions[0] for r in revisions):
        raise ValueError("Colour evidence revisions differ")
    encoded_pixels = None
    if es == "encoded":
        name = encoder.get("file")
        if name != "hlg-ramp.mp4" or ROOT + name not in files or encoder.get("hostPixelCheckRequired") is not True:
            raise ValueError("Encoded HDR requires the actual ramp file")
        with tempfile.TemporaryDirectory(prefix="s23-colour-") as temp:
            video = Path(temp) / name
            video.write_bytes(files[ROOT + name])
            inspect_video(video, 1, True, "off")
            command = ["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(video),
                       "-map", "0:v:0", "-frames:v", "1", "-pix_fmt", "yuv420p10le", "-f", "rawvideo", "-"]
            result = subprocess.run(command, check=True, capture_output=True, timeout=60)
            if result.stderr.strip():
                raise ValueError(result.stderr.decode(errors="replace"))
            if len(result.stdout) != 1024 * 128 * 3:
                raise ValueError("Wrong decoded pixel byte count")
            samples = array.array("H")
            samples.frombytes(result.stdout[:1024 * 128 * 2])
            if sys.byteorder != "little": samples.byteswap()
            encoded_pixels = measure_luma(list(samples), 1024, 128)
    if cs == "recorded":
        v = camera.get("validation", {})
        p = v.get("processing", {})
        if (camera.get("monitorToggled") is not True or v.get("status") != "checked" or
                p.get("cleanupConfirmed") is not True or p.get("error") is not None or
                number(p.get("submittedFrames"), "processed frames") < 3 or
                number(p.get("monitor", {}).get("displayedFrames"), "displayed frames") < 3 or
                v.get("verification", {}).get("lumaBitDepth") != 10):
            raise ValueError("Incomplete processed-camera integration evidence")
    return {"commit": revisions[0], "gpuPixelTests": "passed", "probe": probe,
            "hdrEncoder": encoder, "encodedPixelCheck": encoded_pixels, "cameraIntegration": camera,
            "processedTimingFixturesPresent": True, "timingContentCheck": "separate check_timing.py gate",
            "customLogRecordingEnabled": False, "physicalS23UltraCertified": False,
            "scope": "GPU reference/negative-control tests; HDR encoder and camera availability remain distinct"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify_archive(args.archive), indent=2, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError, subprocess.SubprocessError) as error:
        print(f"Colour validation failed: {error}", file=sys.stderr)
        sys.exit(1)
