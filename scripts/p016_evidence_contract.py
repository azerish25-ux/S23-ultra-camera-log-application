#!/usr/bin/env python3
"""Fail-closed evidence contract for the P016 physical S23 Ultra slice."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import re
from typing import Any

KIND = "p016-physical-capture-bundle"
PHASE = "P016"
MARKER_PROTOCOL = "p016-flash-tone-v1"
REVISION_RE = re.compile(r"[0-9a-f]{40}")
RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}")
S23_ULTRA_MODEL_RE = re.compile(r"SM-S918[A-Za-z0-9-]*", re.IGNORECASE)


class QualificationError(ValueError):
    """Evidence is malformed, contradictory, stale, or insufficient."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise QualificationError(message)


def finite_number(value: Any, label: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be numeric")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    return number


def integer(value: Any, label: str, minimum: int | None = None) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), f"{label} must be an integer")
    if minimum is not None:
        require(value >= minimum, f"{label} must be at least {minimum}")
    return value


def object_at(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    value = mapping.get(key)
    require(isinstance(value, dict), f"{key} must be an object")
    return value


def list_at(mapping: dict[str, Any], key: str) -> list[Any]:
    value = mapping.get(key)
    require(isinstance(value, list), f"{key} must be an array")
    return value


def sha256_file(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing evidence file: {path.name}")
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
            count += len(block)
    require(count > 0, f"empty evidence file: {path.name}")
    return {"algorithm": "SHA-256", "sha256": digest.hexdigest(), "byteCount": count}


def validate_identity(identity: Any, label: str) -> dict[str, Any]:
    require(isinstance(identity, dict), f"{label} identity must be an object")
    require(identity.get("algorithm") == "SHA-256", f"{label} identity algorithm must be SHA-256")
    digest = identity.get("sha256")
    require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
            f"{label} sha256 is invalid")
    integer(identity.get("byteCount"), f"{label} byteCount", 1)
    return identity


def same_identity(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (left.get("algorithm"), left.get("sha256"), left.get("byteCount")) == (
        right.get("algorithm"), right.get("sha256"), right.get("byteCount")
    )


def _validate_device(snapshot: Any, label: str) -> dict[str, Any]:
    require(isinstance(snapshot, dict), f"{label} must be an object")
    manufacturer = snapshot.get("manufacturer")
    model = snapshot.get("model")
    fingerprint = snapshot.get("fingerprint")
    require(isinstance(manufacturer, str) and manufacturer.lower() == "samsung",
            f"{label} is not a Samsung device")
    require(isinstance(model, str) and S23_ULTRA_MODEL_RE.fullmatch(model) is not None,
            f"{label} model is not a Galaxy S23 Ultra (SM-S918*)")
    require(isinstance(fingerprint, str) and len(fingerprint) >= 16,
            f"{label} fingerprint is missing")
    integer(snapshot.get("sdkInt"), f"{label}.sdkInt", 33)
    require(isinstance(snapshot.get("capturedAtUtc"), str) and snapshot["capturedAtUtc"],
            f"{label}.capturedAtUtc is missing")
    for storage_key in ("internalAvailableBytes", "externalAvailableBytes"):
        value = snapshot.get(storage_key)
        require(value is None or (isinstance(value, int) and not isinstance(value, bool) and value >= 0),
                f"{label}.{storage_key} is invalid")
    thermal = snapshot.get("thermalStatus")
    require(thermal is None or (isinstance(thermal, int) and not isinstance(thermal, bool) and 0 <= thermal <= 7),
            f"{label}.thermalStatus is invalid")
    battery = snapshot.get("battery")
    require(isinstance(battery, dict), f"{label}.battery is missing")
    percent = battery.get("percent")
    require(percent is None or (isinstance(percent, (int, float)) and not isinstance(percent, bool)
                                and math.isfinite(float(percent)) and 0 <= float(percent) <= 100),
            f"{label}.battery.percent is invalid")
    return snapshot


def validate_manifest(manifest: Any, expected_revision: str) -> dict[str, Any]:
    require(isinstance(manifest, dict), "device-capture.json must contain an object")
    require(manifest.get("schemaVersion") == 1, "unsupported P016 bundle schema")
    require(manifest.get("kind") == KIND, f"bundle kind must be {KIND}")
    require(manifest.get("phase") == PHASE, f"phase must be {PHASE}")
    revision = manifest.get("sourceRevision")
    require(isinstance(revision, str) and REVISION_RE.fullmatch(revision) is not None,
            "sourceRevision must be a 40-character lowercase commit")
    require(revision == expected_revision, "bundle sourceRevision does not match the requested revision")
    run_id = manifest.get("runId")
    require(isinstance(run_id, str) and RUN_ID_RE.fullmatch(run_id) is not None, "runId is invalid")
    cases = list_at(manifest, "caseIds")
    require(cases == [f"TC-P016-{number:02d}" for number in range(1, 9)],
            "bundle must name TC-P016-01 through TC-P016-08 in order")

    before = _validate_device(manifest.get("deviceBefore"), "deviceBefore")
    after = _validate_device(manifest.get("deviceAfter"), "deviceAfter")
    require(before["model"] == after["model"] and before["fingerprint"] == after["fingerprint"],
            "device identity changed during the run")

    route = object_at(manifest, "route")
    require(route.get("front") is False, "P016 first slice must use a rear route")
    require(isinstance(route.get("logicalId"), str) and route["logicalId"], "logical camera id is missing")
    physical = route.get("physicalId")
    require(physical is None or (isinstance(physical, str) and physical), "physical camera id is invalid")
    require(isinstance(route.get("key"), str) and route["key"], "route key is missing")

    mode = object_at(manifest, "selectedMode")
    width = integer(mode.get("width"), "selectedMode.width", 1)
    height = integer(mode.get("height"), "selectedMode.height", 1)
    fps = integer(mode.get("fps"), "selectedMode.fps", 1)
    require(width <= 1920 and height <= 1080 and fps <= 30,
            "the first slice is not a conservative <=1080p30 configuration")
    require(mode.get("dynamicRange") == "SDR", "the first slice must use the conservative SDR path")
    require(mode.get("processing") == "DIRECT", "the first slice must not require experimental GPU processing")
    require(mode.get("requiresManualExposure") is False,
            "the first slice must not depend on an unconfirmed manual-timing path")
    require(isinstance(mode.get("rateControl"), str) and mode["rateControl"],
            "selectedMode rate-control evidence is missing")

    marker = object_at(manifest, "markerProtocol")
    require(marker.get("id") == MARKER_PROTOCOL, f"marker protocol must be {MARKER_PROTOCOL}")
    require(marker.get("operatorConfirmedReady") is True, "operator did not confirm the timing marker")
    expected_events = list_at(marker, "expectedEventsSeconds")
    require(expected_events == [10, 20, 30, 40, 50, 60], "unexpected marker schedule")

    validation = object_at(manifest, "captureValidation")
    require(validation.get("status") == "checked", "on-device recording validation did not pass")
    require(validation.get("kind") == "recording-validation", "unexpected recording validation kind")
    require(validation.get("videoOnly") is False and validation.get("audioMode") == "MONO",
            "P016 requires the requested mono audio track")
    selected = object_at(validation, "selectedMode")
    for key in ("width", "height", "fps", "dynamicRange", "encoder", "mime"):
        require(selected.get(key) == mode.get(key), f"recording validation selectedMode.{key} differs from the bundle")
    verification = object_at(validation, "verification")
    require(verification.get("firstSyncFrameDecoded") is True, "on-device video decode did not return a frame")
    require(verification.get("firstAudioPcmDecoded") is True, "on-device audio decode did not return PCM")
    require(verification.get("audioRequested") is True and verification.get("audioTrackCount") == 1,
            "on-device validation did not retain exactly one requested audio track")
    require(integer(verification.get("sampleSpanUs"), "verification.sampleSpanUs", 60_000_000) >= 60_000_000,
            "on-device sample span is shorter than sixty seconds")

    attempt = object_at(manifest, "recordingAttempt")
    require(attempt.get("sourceRevision") == revision, "recording-attempt revision is stale")
    require(attempt.get("closed") is True, "recording attempt is not closed")
    classification = object_at(attempt, "classification")
    require(classification.get("recordingSucceeded") is True, "recording attempt did not succeed")
    require(classification.get("fullDecodeVerified") is False and classification.get("physicalCameraCertified") is False,
            "on-device observer must not manufacture independent host/device qualification")

    device_assessment = object_at(manifest, "onDeviceAssessment")
    require(device_assessment.get("durationAtLeast60Seconds") is True,
            "device assessment did not observe a sixty-second span")
    require(device_assessment.get("oneAudioTrackRequestedAndObserved") is True,
            "device assessment did not observe the requested audio track")
    require(device_assessment.get("fullDecodeVerified") is False and
            device_assessment.get("markerEventsVerified") is False and
            device_assessment.get("physicalConfigurationQualified") is False,
            "device-side assessment overclaims independent qualification")
    require(device_assessment.get("enduranceCertified") is False and
            device_assessment.get("higherResolutionQualified") is False,
            "a first slice must not claim endurance or higher-resolution qualification")

    files = object_at(manifest, "files")
    require(set(files) == {"media", "recordingValidation", "recordingAttempt"},
            "bundle file inventory is incomplete or contains unexpected entries")
    for label, required_name in (
        ("media", "capture.mp4"),
        ("recordingValidation", "recording-validation.json"),
        ("recordingAttempt", "recording-attempt.json"),
    ):
        item = object_at(files, label)
        require(item.get("name") == required_name, f"{label} filename is invalid")
        validate_identity(item.get("identity"), label)

    non_claims = list_at(manifest, "nonClaims")
    for required in ("endurance", "unlimited recording", "higher-resolution modes", "sensor-derived Log", "cinema-camera equivalence"):
        require(any(required.lower() in str(entry).lower() for entry in non_claims),
                f"bundle is missing the non-claim: {required}")
    return manifest
