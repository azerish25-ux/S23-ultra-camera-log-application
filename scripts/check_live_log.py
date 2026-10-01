#!/usr/bin/env python3
"""Validate live-lab evidence without turning missing hardware into a successful codec test."""
from __future__ import annotations
import argparse
import json
import tarfile


def validate(gpu: dict, backend: dict, screen: dict) -> dict:
    revisions = {item.get("appCommit") for item in (gpu, backend, screen)}
    if len(revisions) != 1 or not next(iter(revisions)) or "local-unversioned" in revisions:
        raise ValueError("Missing or mixed live-lab source revisions")
    if gpu.get("status") != "passed" or gpu.get("bayerReductionCases") != 12:
        raise ValueError("Missing GPU Bayer/reduction comparison")
    if not 0 <= gpu.get("maximumLogRgbError", 99) <= .001 or not 0 <= gpu.get("maximumP010CodeError", 99) <= 2:
        raise ValueError("GPU reference error exceeded")
    if gpu.get("sensorPrecisionMeasured") is not False or backend.get("sensorPrecisionMeasured") is not False:
        raise ValueError("Synthetic evidence cannot certify the sensor")
    if screen.get("status") != "passed" or screen.get("implicitRecording") is not False:
        raise ValueError("Live UI safety evidence missing")
    accepted = [r for r in backend.get("routes", []) if r.get("status") == "qualified"]
    status = backend.get("status")
    if status == "qualified":
        if len(accepted) != 1:
            raise ValueError("Qualified status requires one qualified route")
        route = accepted[0]
        for name in ("positive", "selectedSize"):
            proof = route[name]
            if proof.get("passed") is not True or proof.get("fullDecodeVerified") is not True:
                raise ValueError("Missing positive decoded-pixel proof")
            if proof.get("lumaBitDepth") != 10 or proof.get("chromaBitDepth") != 10:
                raise ValueError("Not ten-bit")
            if (proof.get("colorPrimariesCode"), proof.get("transferCharacteristicsCode"), proof.get("matrixCoefficientsCode")) != (2, 2, 1):
                raise ValueError("Wrong Log interpretation contract")
        if route.get("eightBitNegative", {}).get("passed") is not False:
            raise ValueError("Eight-bit negative control was not rejected")
    elif status in ("unavailable", "query_failed"):
        if accepted or backend.get("selectedCodec") is not None:
            raise ValueError("Unavailable hardware was labelled qualified")
    else:
        raise ValueError("Unknown backend state")
    return {"appCommit": next(iter(revisions)), "gpuReference": "passed", "backend": status,
            "liveCameraTested": False, "physicalCameraCertified": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    args = parser.parse_args()
    with tarfile.open(args.archive) as archive:
        def read(name):
            entry = archive.getmember(f"files/exports/live-log/{name}")
            if not entry.isfile() or entry.size > 2_000_000:
                raise ValueError("Invalid evidence member")
            return json.load(archive.extractfile(entry))
        print(json.dumps(validate(read("gpu-test.json"), read("backend-test.json"), read("screen-test.json")), indent=2))


if __name__ == "__main__":
    main()
