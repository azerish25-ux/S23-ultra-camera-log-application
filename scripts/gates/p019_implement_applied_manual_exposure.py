#!/usr/bin/env python3
"""P019 host gate for applied manual exposure.

Requested ISO and shutter are not sensor observations. Units and sensor limits
are validated. Clamping is published only as a visible effective target. The
required lock transition must complete before a tolerance comparison can match.
Missing metadata stays a different status from a measured mismatch.

The authored fixture asks for a shutter longer than the frame period and an ISO
result that remains at the previous automatic value. The user-visible record
shows the effective target and that mismatch. Recording cannot claim confirmed
manual control. Showing the requested ISO as an observed sensor value is the
deliberate mutant and is rejected.

This module does not probe a device, does not qualify a physical S23, and does
not execute TC-P019-01 through TC-P019-08.
"""

from __future__ import annotations

from typing import Any


PHASE_ID = "P019"
CASE_ID = "P019"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
FIXTURE_ID = "s23-applied-manual-exposure-fixture"

METHOD = (
    "Validate units and sensor limits, clamp only through a visible effective "
    "target, wait for the required lock transition, and compare actual result "
    "values against defined tolerances. Preserve the difference between missing "
    "metadata and a measured mismatch."
)
FIXTURE = (
    "A requested shutter longer than the frame period and an ISO result that "
    "remains at the previous automatic value."
)
ORACLE = (
    "The user sees the effective target and mismatch; recording cannot claim "
    "confirmed manual control."
)
MUTANT = "Show requested ISO as if it were an observed sensor value."

ISO_TOLERANCE = 0.05
EXPOSURE_TOLERANCE = 0.05
FRAME_TOLERANCE = 0.03
REQUIRED_LOCK = "manual_exposure_locked"
CONFIRMED_CLAIM = "confirmed-manual-control"
MUTANT_CLAIM = "requested-iso-as-observed"

_DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "fixtureId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "tolerances",
    "sensorLimits",
    "request",
    "lock",
    "result",
    "presentation",
}
_TOLERANCE_KEYS = {"isoFraction", "exposureFraction", "frameDurationFraction"}
_LIMIT_KEYS = {"isoMin", "isoMax", "shutterMinNs", "shutterMaxNs"}
_REQUEST_KEYS = {"iso", "shutterNs", "framePeriodNs", "aeMode"}
_LOCK_KEYS = {"required", "observed"}
_RESULT_KEYS = {"iso", "shutterNs", "frameDurationNs", "previousAutomaticIso", "metadata"}
_METADATA_KEYS = {"iso", "shutter", "frameDuration"}
_METADATA_STATES = {"present", "missing"}
_AE_MODES = {"off", "on"}
_PRESENTATIONS = {"observed", "requested_as_observed"}
_ASSESS_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"withheld", "rejected", "result_matched"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _positive_int(value: object, context: str) -> int:
    require(type(value) is int and value > 0, context + " must be a positive int")
    return value


def _fraction(value: object, context: str) -> float:
    require(type(value) in (int, float) and type(value) is not bool, context + " must be a number")
    require(0 < float(value) < 1, context + " must be a fraction between 0 and 1")
    return float(value)


def _optional_positive_int(value: object, context: str) -> int | None:
    if value is None:
        return None
    return _positive_int(value, context)


def within_tolerance(actual: int, target: int, tolerance: float) -> bool:
    """Application tolerance: absolute error within max(1, target * fraction).

    This is host arithmetic, not a calibration claim.
    """
    limit = max(1.0, target * tolerance)
    return abs(float(actual) - float(target)) <= limit


def _channel_status(metadata: str, actual: int | None, target: int, tolerance: float) -> str:
    """Return missing_metadata, measured_mismatch, or within_tolerance.

    Missing metadata is not rewritten as a mismatch, and a present value that
    disagrees is not rewritten as missing.
    """
    if metadata == "missing":
        require(actual is None, "missing metadata must not carry a numeric observation")
        return "missing_metadata"
    require(actual is not None, "present metadata requires a numeric observation")
    if within_tolerance(actual, target, tolerance):
        return "within_tolerance"
    return "measured_mismatch"


def effective_target(request: dict, limits: dict) -> dict[str, Any]:
    """Clamp ISO and shutter through limits. Shutter also clamps to the frame.

    The returned target is the only value a comparison may use. The requested
    shutter is left unchanged so a frame-period clamp stays visible.
    """
    iso = _positive_int(request["iso"], "request.iso")
    shutter = _positive_int(request["shutterNs"], "request.shutterNs")
    frame = _positive_int(request["framePeriodNs"], "request.framePeriodNs")
    iso_min = _positive_int(limits["isoMin"], "sensorLimits.isoMin")
    iso_max = _positive_int(limits["isoMax"], "sensorLimits.isoMax")
    shutter_min = _positive_int(limits["shutterMinNs"], "sensorLimits.shutterMinNs")
    shutter_max = _positive_int(limits["shutterMaxNs"], "sensorLimits.shutterMaxNs")
    require(iso_min <= iso_max, "sensor ISO minimum exceeds maximum")
    require(shutter_min <= shutter_max, "sensor shutter minimum exceeds maximum")
    upper = min(shutter_max, frame)
    require(shutter_min <= upper, "sensor shutter minimum exceeds the frame period")
    clamped_iso = min(max(iso, iso_min), iso_max)
    clamped_shutter = min(max(shutter, shutter_min), upper)
    return {
        "iso": clamped_iso,
        "shutterNs": clamped_shutter,
        "framePeriodNs": frame,
        "isoClamped": clamped_iso != iso,
        "shutterClampedToFrame": shutter > frame,
        "shutterClampedToSensor": shutter > shutter_max or shutter < shutter_min,
        "visible": True,
    }


def validate_fixture(document: dict) -> None:
    """Raise ValueError unless document is the P019 manual-exposure fixture shape."""
    _exact_keys(document, _DOCUMENT_KEYS, "manual exposure fixture")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE_ID, "phase must be P019")
    require(document["fixtureId"] == FIXTURE_ID, "unexpected fixtureId")
    require(document["implementationBaseRevision"] == BASE_REVISION,
            "unexpected implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    tolerances = _exact_keys(document["tolerances"], _TOLERANCE_KEYS, "tolerances")
    require(_fraction(tolerances["isoFraction"], "isoFraction") == ISO_TOLERANCE, "iso tolerance drifted")
    require(
        _fraction(tolerances["exposureFraction"], "exposureFraction") == EXPOSURE_TOLERANCE,
        "exposure tolerance drifted",
    )
    require(
        _fraction(tolerances["frameDurationFraction"], "frameDurationFraction") == FRAME_TOLERANCE,
        "frame tolerance drifted",
    )
    limits = _exact_keys(document["sensorLimits"], _LIMIT_KEYS, "sensorLimits")
    request = _exact_keys(document["request"], _REQUEST_KEYS, "request")
    require(request["aeMode"] in _AE_MODES, "aeMode must be off or on")
    lock = _exact_keys(document["lock"], _LOCK_KEYS, "lock")
    require(lock["required"] == REQUIRED_LOCK, "required lock must be manual_exposure_locked")
    require(isinstance(lock["observed"], str) and lock["observed"].strip(),
            "observed lock must be a non-empty string")
    result = _exact_keys(document["result"], _RESULT_KEYS, "result")
    metadata = _exact_keys(result["metadata"], _METADATA_KEYS, "result.metadata")
    for name in ("iso", "shutter", "frameDuration"):
        require(metadata[name] in _METADATA_STATES, f"result.metadata.{name} is invalid")
    _positive_int(result["previousAutomaticIso"], "result.previousAutomaticIso")
    for name, state in (
        ("iso", metadata["iso"]),
        ("shutterNs", metadata["shutter"]),
        ("frameDurationNs", metadata["frameDuration"]),
    ):
        if state == "missing":
            require(result[name] is None, f"result.{name} must be null when metadata is missing")
        else:
            _positive_int(result[name], f"result.{name}")
    require(document["presentation"] in _PRESENTATIONS, "presentation is invalid")
    effective_target(request, limits)


def _preserved(document: dict, target: dict[str, Any], statuses: dict[str, str]) -> list[str]:
    request = document["request"]
    result = document["result"]
    limits = document["sensorLimits"]
    observed_iso = "missing" if result["iso"] is None else str(result["iso"])
    observed_shutter = "missing" if result["shutterNs"] is None else str(result["shutterNs"])
    observed_frame = "missing" if result["frameDurationNs"] is None else str(result["frameDurationNs"])
    return [
        f"requested-iso:{request['iso']}",
        f"requested-shutter-ns:{request['shutterNs']}",
        f"frame-period-ns:{request['framePeriodNs']}",
        f"effective-iso:{target['iso']}",
        f"effective-shutter-ns:{target['shutterNs']}",
        f"observed-iso:{observed_iso}",
        f"observed-shutter-ns:{observed_shutter}",
        f"observed-frame-ns:{observed_frame}",
        f"previous-automatic-iso:{result['previousAutomaticIso']}",
        f"sensor-iso-min:{limits['isoMin']}",
        f"sensor-iso-max:{limits['isoMax']}",
        f"sensor-shutter-min-ns:{limits['shutterMinNs']}",
        f"sensor-shutter-max-ns:{limits['shutterMaxNs']}",
        f"iso-status:{statuses['iso']}",
        f"shutter-status:{statuses['shutter']}",
        f"frame-status:{statuses['frame']}",
        "effective-target-visible",
    ]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS, "decision must not be qualified or allowed")
    require(decision not in {"qualified", "allowed"}, "decision must not be qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons), "reasons required")
    for items in (rejected, preserved, questions):
        require(all(isinstance(item, str) and item for item in items), "result lists must be non-empty strings")
    require(CONFIRMED_CLAIM in rejected, "confirmed manual control must stay rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == _ASSESS_KEYS, "assessment keys drifted")
    return result


def assess(document: dict) -> dict[str, Any]:
    """Compare a manual-exposure fixture without treating the request as the result.

    The observed ISO is read only from result.iso. presentation
    requested_as_observed is the mutant and is rejected. A shutter longer than
    the frame period changes the visible effective target, not the request.
    Decision is never qualified or allowed.
    """
    validate_fixture(document)
    request = document["request"]
    limits = document["sensorLimits"]
    tolerances = document["tolerances"]
    result = document["result"]
    metadata = result["metadata"]
    target = effective_target(request, limits)
    statuses = {
        "iso": _channel_status(metadata["iso"], result["iso"], target["iso"], tolerances["isoFraction"]),
        "shutter": _channel_status(
            metadata["shutter"], result["shutterNs"], target["shutterNs"], tolerances["exposureFraction"]
        ),
        "frame": _channel_status(
            metadata["frameDuration"],
            result["frameDurationNs"],
            target["framePeriodNs"],
            tolerances["frameDurationFraction"],
        ),
    }
    preserved = _preserved(document, target, statuses)
    questions = [
        "host fixture is not a physical S23 qualification",
        "numeric comparison is not cinema-camera equivalence",
    ]
    rejected = [CONFIRMED_CLAIM]
    reasons = [
        (
            f"user-visible effective target iso {target['iso']} "
            f"shutterNs {target['shutterNs']}"
        ),
        "recording cannot claim confirmed manual control",
    ]
    if target["shutterClampedToFrame"]:
        reasons.append(
            f"requested shutterNs {request['shutterNs']} is longer than frame period "
            f"{request['framePeriodNs']} and was clamped only on the visible effective target"
        )
    if target["isoClamped"]:
        reasons.append(
            f"requested iso {request['iso']} was clamped to visible effective iso {target['iso']}"
        )
    for name in ("iso", "shutter", "frame"):
        status = statuses[name]
        if status == "missing_metadata":
            reasons.append(f"{name} missing metadata")
        elif status == "measured_mismatch":
            reasons.append(f"{name} measured mismatch")
        else:
            reasons.append(f"{name} within tolerance of the visible effective target")
    if (
        statuses["iso"] == "measured_mismatch"
        and result["iso"] == result["previousAutomaticIso"]
        and result["iso"] != target["iso"]
    ):
        reasons.append(
            f"user-visible iso mismatch observed {result['iso']} "
            f"previous automatic {result['previousAutomaticIso']} effective {target['iso']}"
        )

    if document["presentation"] == "requested_as_observed":
        rejected.insert(0, MUTANT_CLAIM)
        reasons.append(MUTANT)
        reasons.append("requested ISO was not copied into the observed sensor value")
        require(f"observed-iso:{request['iso']}" not in preserved or result["iso"] == request["iso"],
                "mutant must not replace a different observation")
        if result["iso"] != request["iso"]:
            require(f"observed-iso:{request['iso']}" not in preserved,
                    "mutant replaced the observed ISO")
        return _result("rejected", reasons, rejected, preserved, questions)

    lock_ready = document["lock"]["observed"] == REQUIRED_LOCK
    if not lock_ready:
        reasons.append("required lock transition has not completed")
        questions.append("manual exposure lock transition is still open")
    if request["aeMode"] != "off":
        reasons.append("auto exposure is still active")
    matched = (
        lock_ready
        and request["aeMode"] == "off"
        and all(status == "within_tolerance" for status in statuses.values())
    )
    if matched:
        reasons.append("host arithmetic matched the visible effective target")
        decision = "result_matched"
    else:
        reasons.append("confirmed manual control stays withheld")
        decision = "withheld"
    built = _result(decision, reasons, rejected, preserved, questions)
    if document["presentation"] == "observed" and result["iso"] != request["iso"]:
        require(f"observed-iso:{request['iso']}" not in built["preservedResults"],
                "requested ISO must not be shown as the observed sensor value")
    return built
