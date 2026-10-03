#!/usr/bin/env python3
"""Validate one real P016 S23 Ultra bundle without upgrading it to endurance proof."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from p016_evidence_contract import (  # noqa: E402
    KIND,
    MARKER_PROTOCOL,
    PHASE,
    REVISION_RE,
    QualificationError,
    finite_number,
    integer,
    object_at,
    require,
    same_identity,
    sha256_file,
    validate_identity,
    validate_manifest,
)
from p016_marker_analysis import (  # noqa: E402
    detect_marker_from_series,
    inspect_cadence,
    inspect_marker,
)


def _load_check_video_module() -> Any:
    path = Path(__file__).with_name("check_video.py")
    spec = importlib.util.spec_from_file_location("_s23_check_video", path)
    require(spec is not None and spec.loader is not None, "cannot load check_video.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def classify(manifest: dict[str, Any], media: dict[str, Any], marker: dict[str, Any],
             cadence: dict[str, Any]) -> dict[str, Any]:
    validation = object_at(manifest, "captureValidation")
    verification = object_at(validation, "verification")
    mode = object_at(manifest, "selectedMode")
    expected_identity = validate_identity(object_at(object_at(manifest, "files"), "media").get("identity"), "media")
    actual_identity = validate_identity(media.get("mediaIdentity"), "decoded media")
    require(same_identity(expected_identity, actual_identity), "fully decoded media identity differs from the phone bundle")
    report_identity = validate_identity(verification.get("mediaIdentity"), "on-device media")
    require(same_identity(report_identity, actual_identity), "host media differs from the on-device checked output")

    require(media.get("fullDecodePassed") is True, "video was not fully decoded")
    require(media.get("audioPresent") is True and media.get("audioFullDecodePassed") is True,
            "requested audio was not fully decoded")
    require(finite_number(media.get("durationSeconds"), "decoded duration") >= 60.0,
            "decoded container duration is shorter than sixty seconds")
    require(finite_number(media.get("packetSpanSeconds"), "decoded packet span") >= 60.0,
            "decoded packet timestamps span less than sixty seconds")
    stream = object_at(media, "stream")
    require(integer(stream.get("width"), "decoded width", 1) == mode.get("width") and
            integer(stream.get("height"), "decoded height", 1) == mode.get("height"),
            "decoded output geometry differs from the selected mode")
    require(marker.get("protocol") == MARKER_PROTOCOL and marker.get("verified") is True and
            integer(marker.get("pairedEventCount"), "paired marker count", 2) >= 2,
            "visible/acoustic timing events were not independently verified")
    require(marker.get("physicalLipSyncVerified") is False,
            "uncalibrated marker playback must not be labelled physical lip-sync proof")
    require(cadence.get("status") in {"pass", "warning"}, "cadence result is missing")

    before = object_at(manifest, "deviceBefore")
    after = object_at(manifest, "deviceAfter")
    thermal_observed = before.get("thermalStatus") is not None and after.get("thermalStatus") is not None
    storage_observed = before.get("internalAvailableBytes") is not None and after.get("internalAvailableBytes") is not None
    require(thermal_observed and storage_observed, "thermal and storage observations are required")

    cadence_passed = cadence["status"] == "pass"
    status = "qualified_exact_60s_slice" if cadence_passed else "slice_retained_cadence_warning"
    return {
        "schemaVersion": 1,
        "kind": "p016-physical-qualification-report",
        "phase": PHASE,
        "runId": manifest["runId"],
        "sourceRevision": manifest["sourceRevision"],
        "status": status,
        "physicalSliceCompleted": True,
        "playbackIntegrity": "fully_decoded",
        "audioIntegrity": "fully_decoded",
        "timingEventStatus": "verified_repeating_flash_tone",
        "cadenceStatus": cadence["status"],
        "cadenceQualifiedForThisSlice": cadence_passed,
        "exactConfigurationQualified": cadence_passed,
        "retainedWithCadenceWarning": not cadence_passed,
        "enduranceCertified": False,
        "higherResolutionQualified": False,
        "sensorDerivedLogQualified": False,
        "physicalLipSyncVerified": False,
        "cinemaCameraEquivalent": False,
        "route": manifest["route"],
        "selectedMode": mode,
        "deviceBefore": before,
        "deviceAfter": after,
        "media": media,
        "marker": marker,
        "cadence": cadence,
        "boundIdentities": manifest["files"],
        "openGates": [
            "warm and repeated runs",
            "long-duration endurance",
            "additional rear lens routes",
            "4K/8K and HDR qualification",
            "calibrated physical audiovisual synchronization",
            "sensor-derived Log and dynamic-range measurement",
        ],
    }


def validate_bundle(directory: Path, expected_revision: str) -> dict[str, Any]:
    require(REVISION_RE.fullmatch(expected_revision) is not None,
            "--expected-revision must be a 40-character lowercase commit")
    manifest_path = directory / "device-capture.json"
    require(manifest_path.is_file(), "device-capture.json is missing")
    manifest = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")), expected_revision)

    files = object_at(manifest, "files")
    for label in ("media", "recordingValidation", "recordingAttempt"):
        item = object_at(files, label)
        actual = sha256_file(directory / item["name"])
        expected = validate_identity(item.get("identity"), label)
        require(same_identity(actual, expected), f"{label} file identity differs from device-capture.json")

    copied_validation = json.loads((directory / "recording-validation.json").read_text(encoding="utf-8"))
    copied_attempt = json.loads((directory / "recording-attempt.json").read_text(encoding="utf-8"))
    require(copied_validation == manifest["captureValidation"], "copied recording validation differs from the manifest")
    require(copied_attempt == manifest["recordingAttempt"], "copied recording attempt differs from the manifest")

    video_module = _load_check_video_module()
    media = video_module.inspect(directory / "capture.mp4", 60.0, False, "on", 1)
    marker = inspect_marker(directory / "capture.mp4")
    cadence = inspect_cadence(directory / "capture.mp4", int(object_at(manifest, "selectedMode")["fps"]))
    return classify(manifest, media, marker, cadence)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="Directory pulled from the P016 Android instrumentation")
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--output", type=Path, help="Write the complete qualification report atomically")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        report = validate_bundle(args.bundle, args.expected_revision)
        payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.output.with_suffix(args.output.suffix + ".tmp")
            temporary.write_text(payload, encoding="utf-8")
            temporary.replace(args.output)
        print(payload, end="")
        return 0 if report["status"] == "qualified_exact_60s_slice" else 2
    except (OSError, KeyError, TypeError, json.JSONDecodeError, QualificationError,
            subprocess.SubprocessError) as error:
        print(f"P016 qualification withheld: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
