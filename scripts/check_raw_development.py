#!/usr/bin/env python3
"""Check native on-device developer evidence without converting unavailable codecs to a pass."""
import json
from pathlib import Path
import sys
import tarfile


def verify(path: Path) -> dict:
    wanted = {"native-ui", "android-math", "p010-codec"}
    reports = {}
    with tarfile.open(path) as archive:
        for item in archive:
            for name in wanted:
                if item.name == f"files/exports/raw-development/{name}.json":
                    if not item.isfile() or not 0 < item.size <= 1_048_576 or name in reports:
                        raise ValueError("Invalid or duplicate RAW developer evidence")
                    with archive.extractfile(item) as source:
                        reports[name] = json.load(source)
    if set(reports) != wanted:
        raise ValueError("Missing native RAW development evidence")
    ui = reports["native-ui"]
    math = reports["android-math"]
    if ui.get("status") != "passed" or not all(ui.get(k) is True for k in
            ("sourceCrcChecked", "profileImported", "activityRecreated", "sourceHashUnchanged")):
        raise ValueError("Native UI/source/profile acceptance failed")
    if math.get("status") != "passed" or math.get("distinctMathLevels") != 1024 or not all(math.get(k) is True for k in
            ("referenceGreyMatched", "corruptionRejected", "sourceRetained")):
        raise ValueError("Android RAW reference arithmetic failed")
    codec = reports["p010-codec"]
    if codec.get("status") == "unavailable":
        if codec.get("encodedPixelsTested") is not False or not codec.get("reason"):
            raise ValueError("Unavailable codec was incorrectly represented")
    elif codec.get("status") == "passed":
        q, v = codec.get("qualification", {}), codec.get("verification", {})
        if (q.get("positive", {}).get("passed") is not True or q.get("eightBitNegative", {}).get("passed") is not False or
                codec.get("encodedPixelsTested") is not True or v.get("fullDecodeVerified") is not True or
                v.get("decodedFrames") != 8 or v.get("lumaBitDepth") != 10 or v.get("chromaBitDepth") != 10 or
                (v.get("colorPrimariesCode"), v.get("transferCharacteristicsCode"), v.get("matrixCoefficientsCode")) != (2, 2, 1)):
            raise ValueError("10-bit encoder/decode/negative-control acceptance failed")
    else:
        raise ValueError("Unexpected codec status")
    if not all(r.get("physicalCameraCertified") is False and r.get("appCommit") for r in reports.values()):
        raise ValueError("Missing provenance or false physical-camera certification")
    return {"nativeUi": "passed", "androidReferenceMath": "passed", "codecRoute": codec["status"],
            "encodedPixelsTested": codec["encodedPixelsTested"], "physicalCameraCertified": False}


if __name__ == "__main__":
    try:
        print(json.dumps(verify(Path(sys.argv[1])), indent=2))
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError) as error:
        raise SystemExit(f"RAW development evidence rejected: {error}")
