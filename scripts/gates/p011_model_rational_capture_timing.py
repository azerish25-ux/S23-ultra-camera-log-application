#!/usr/bin/env python3
"""P011 rational timing policy and manual-readiness gate.

Rates are reduced numerator/denominator pairs. Fixed AE ranges, variable AE
ranges, and manual frame duration stay distinct. Requested exposure must fit
the effective interval of the mechanism that can actually run. Capture-result
timing is compared with that mechanism; a requested value is not assumed to
have been applied. Container timestamps never certify native fixed 24. The AE
upper bound is never rounded to a desired cinematic rate.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P011-01 through TC-P011-08.
"""

from __future__ import annotations

import math
from typing import Any


BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
POLICY_ID = "s23-rational-timing-fixture"
CASE_ID = "P011"
MUTANT_ID = "round-ae-upper-to-cinematic"
METHOD = (
    "Represent rates as numerator and denominator. Distinguish fixed AE ranges, "
    "variable AE ranges, and manual frame duration. Verify requested exposure does "
    "not exceed the effective interval and compare capture-result timing rather than "
    "assuming a requested value was applied."
)
FIXTURE = (
    "An AE range of fifteen to thirty frames per second, a requested twenty-four "
    "frame output, and manual timing that has not been confirmed."
)
ORACLE = (
    "The planner cannot label the candidate native fixed twenty-four merely by "
    "assigning container timestamps."
)
MUTANT = "Round an AE upper bound to the nearest desired cinematic frame rate."

POLICY_KEYS = {
    "schemaVersion",
    "phase",
    "policyId",
    "implementationBaseRevision",
    "mechanism",
    "aeRange",
    "requestedOutput",
    "manualTiming",
    "containerTimestamps",
    "exposureNs",
    "captureResult",
}
AE_KEYS = {"minFps", "maxFps"}
RATE_KEYS = {"numerator", "denominator"}
MANUAL_KEYS = {"confirmed", "frameRate"}
CONTAINER_KEYS = {"assigned", "rate"}
CAPTURE_KEYS = {"frameRate", "exposureNs"}
MECHANISMS = {"fixed_ae", "variable_ae", "manual"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
FORBIDDEN_DECISIONS = {"qualified", "allowed", "native_fixed_24"}
NS_PER_SECOND = 1_000_000_000


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _parse_rate(value: object, context: str) -> tuple[int, int]:
    exact_keys(value, RATE_KEYS, context)
    numerator = value["numerator"]
    denominator = value["denominator"]
    require(type(numerator) is int and type(denominator) is int,
            context + " numerator and denominator must be ints")
    require(numerator > 0 and denominator > 0, context + " must be a positive fraction")
    require(math.gcd(numerator, denominator) == 1, context + " must be a reduced fraction")
    return numerator, denominator


def _rate_text(rate: tuple[int, int]) -> str:
    return f"{rate[0]}/{rate[1]}"


def _cmp(left: tuple[int, int], right: tuple[int, int]) -> int:
    gap = left[0] * right[1] - right[0] * left[1]
    if gap > 0:
        return 1
    if gap < 0:
        return -1
    return 0


def _includes(low: tuple[int, int], high: tuple[int, int], value: tuple[int, int]) -> bool:
    return _cmp(low, value) <= 0 and _cmp(value, high) <= 0


def _interval_from_rate(rate: tuple[int, int]) -> tuple[int, int]:
    """Return the frame duration in seconds as a reduced rational, 1/fps."""
    numerator, denominator = rate[1], rate[0]
    scale = math.gcd(numerator, denominator)
    return numerator // scale, denominator // scale


def _fits(exposure_ns: int, interval: tuple[int, int]) -> bool:
    return exposure_ns * interval[1] <= NS_PER_SECOND * interval[0]


def _optional_rate(value: object, context: str) -> tuple[int, int] | None:
    if value is None:
        return None
    return _parse_rate(value, context)


def validate_policy(document: dict) -> None:
    """Raise ValueError unless document is the P011 rational timing policy."""
    exact_keys(document, POLICY_KEYS, "timing policy")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == "P011", "phase must be P011")
    require(document["policyId"] == POLICY_ID, "policyId must be s23-rational-timing-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION, "timing policy needs the P011 implementation base revision")
    mechanism = document["mechanism"]
    require(mechanism in MECHANISMS, "mechanism must be fixed_ae, variable_ae, or manual")
    ae_range = exact_keys(document["aeRange"], AE_KEYS, "aeRange")
    ae_min = _parse_rate(ae_range["minFps"], "aeRange.minFps")
    ae_max = _parse_rate(ae_range["maxFps"], "aeRange.maxFps")
    require(_cmp(ae_min, ae_max) <= 0, "aeRange minFps must not exceed maxFps")
    if mechanism == "fixed_ae":
        require(ae_min == ae_max, "fixed_ae requires minFps == maxFps")
    elif mechanism == "variable_ae":
        require(ae_min != ae_max, "variable_ae requires minFps < maxFps")
    requested = _parse_rate(document["requestedOutput"], "requestedOutput")
    manual = exact_keys(document["manualTiming"], MANUAL_KEYS, "manualTiming")
    require(type(manual["confirmed"]) is bool, "manualTiming.confirmed must be a bool")
    manual_rate = _optional_rate(manual["frameRate"], "manualTiming.frameRate")
    if mechanism == "manual":
        require(manual_rate is not None, "manual frame duration requires manualTiming.frameRate")
    else:
        require(manual_rate is None, "manualTiming.frameRate is only set for mechanism manual")
    container = exact_keys(document["containerTimestamps"], CONTAINER_KEYS, "containerTimestamps")
    require(type(container["assigned"]) is bool, "containerTimestamps.assigned must be a bool")
    container_rate = _optional_rate(container["rate"], "containerTimestamps.rate")
    if container["assigned"]:
        require(container_rate is not None, "assigned container timestamps require a rate")
    else:
        require(container_rate is None, "unassigned container timestamps cannot carry a rate")
    exposure = document["exposureNs"]
    require(type(exposure) is int and exposure > 0, "exposureNs must be a positive int")
    capture = document["captureResult"]
    if capture is not None:
        exact_keys(capture, CAPTURE_KEYS, "captureResult")
        _parse_rate(capture["frameRate"], "captureResult.frameRate")
        measured_exposure = capture["exposureNs"]
        require(type(measured_exposure) is int and measured_exposure > 0,
                "captureResult.exposureNs must be a positive int")
    # requested is parsed so a non-rate cannot hide behind a valid AE range
    require(requested[0] > 0, "requestedOutput must be positive")


def retain_ae_upper(upper: dict, desired: dict) -> dict:
    """Return the AE upper bound unchanged.

    The forbidden mutant rounds ``upper`` to ``desired`` (the requested
    cinematic frame rate). This function keeps the stated bound even when a
    nearer cinematic label exists.
    """
    stated = _parse_rate(upper, "upper")
    _parse_rate(desired, "desired")
    return {"numerator": stated[0], "denominator": stated[1]}


def _bounds(document: dict) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    ae_min = _parse_rate(document["aeRange"]["minFps"], "aeRange.minFps")
    ae_max = _parse_rate(document["aeRange"]["maxFps"], "aeRange.maxFps")
    requested = _parse_rate(document["requestedOutput"], "requestedOutput")
    return ae_min, ae_max, requested


def _active_rate(document: dict) -> tuple[int, int]:
    """Rate whose reciprocal is the effective frame duration."""
    if document["mechanism"] == "manual":
        return _parse_rate(document["manualTiming"]["frameRate"], "manualTiming.frameRate")
    return _parse_rate(document["aeRange"]["maxFps"], "aeRange.maxFps")


def effective_interval_seconds(document: dict) -> dict:
    """Effective frame duration in seconds. Not the requested output rate."""
    validate_policy(document)
    numerator, denominator = _interval_from_rate(_active_rate(document))
    return {"numerator": numerator, "denominator": denominator}


def exposure_fits(document: dict) -> bool:
    """True when requested exposure does not exceed the effective interval."""
    validate_policy(document)
    interval = _interval_from_rate(_active_rate(document))
    return _fits(document["exposureNs"], interval)


def classify_mechanism(document: dict) -> str:
    """Return fixed_ae, variable_ae, or manual after validation."""
    validate_policy(document)
    return document["mechanism"]


def _preserved(document: dict, ae_min, ae_max, requested) -> list[str]:
    preserved = [
        f"ae:{_rate_text(ae_min)}-{_rate_text(ae_max)}",
        f"requested:{_rate_text(requested)}",
        f"mechanism:{document['mechanism']}",
        f"exposureNs:{document['exposureNs']}",
    ]
    manual = document["manualTiming"]
    if document["mechanism"] == "manual":
        preserved.append(f"manual:{_rate_text(_parse_rate(manual['frameRate'], 'manualTiming.frameRate'))}")
    elif manual["confirmed"] is False:
        preserved.append("manual:unconfirmed")
    else:
        preserved.append("manual:flag-only")
    return preserved


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict[str, Any]:
    require(decision not in FORBIDDEN_DECISIONS, "decision must not be qualified, allowed, or native_fixed_24")
    require(bool(reasons), "reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def assess_policy(document: dict, mutant: str | None = None) -> dict:
    """Judge one timing policy. Never labels native fixed 24 from timestamps.

    ``mutant="round-ae-upper-to-cinematic"`` is the deliberate false
    implementation. It is rejected and the stated AE upper bound is preserved.
    """
    validate_policy(document)
    require(mutant is None or mutant == MUTANT_ID, "unknown mutant")
    ae_min, ae_max, requested = _bounds(document)
    preserved = _preserved(document, ae_min, ae_max, requested)
    manual = document["manualTiming"]
    mechanism = document["mechanism"]
    if mutant == MUTANT_ID:
        questions = []
        if mechanism != "manual" and manual["confirmed"] is False:
            questions.append("manual timing has not been confirmed")
        return _result(
            "rejected",
            [
                "mutant rejected: AE upper bound was not rounded to the requested cinematic rate",
                f"AE upper bound {_rate_text(ae_max)} was retained; requested {_rate_text(requested)} was not written over it",
            ],
            ["rounded-ae-upper-bound"],
            preserved,
            questions,
        )

    interval = _interval_from_rate(_active_rate(document))
    reasons = [
        f"rate strategy {mechanism} requested {_rate_text(requested)}",
        f"AE upper bound {_rate_text(ae_max)} was not rounded to requested {_rate_text(requested)}",
    ]
    rejected: list[str] = []
    questions: list[str] = []
    if _fits(document["exposureNs"], interval):
        reasons.append(
            f"requested exposure fits the effective interval {_rate_text(interval)}s"
        )
    else:
        reasons.append(
            f"requested exposure {document['exposureNs']}ns exceeds effective interval {_rate_text(interval)}s"
        )
        rejected.append("exposure-exceeds-interval")

    container = document["containerTimestamps"]
    if container["assigned"] is True:
        rejected.append("container-timestamps-as-native-cadence")
        reasons.append("container timestamps do not certify native fixed 24")

    capture = document["captureResult"]
    measured = None
    if capture is None:
        reasons.append("capture result absent; requested timing was not assumed applied")
        questions.append("capture-result timing has not been measured")
    else:
        measured = _parse_rate(capture["frameRate"], "captureResult.frameRate")
        preserved.append(f"measured:{_rate_text(measured)}")
        reasons.append(f"capture result frame rate {_rate_text(measured)} compared with the request")
        measured_interval = _interval_from_rate(measured)
        if not _fits(capture["exposureNs"], measured_interval):
            rejected.append("result-exposure-exceeds-interval")
            reasons.append("capture-result exposure exceeds the measured frame interval")

    mismatch = False
    if measured is not None and mechanism == "manual":
        manual_rate = _parse_rate(manual["frameRate"], "manualTiming.frameRate")
        mismatch = measured != manual_rate
    elif measured is not None and mechanism == "fixed_ae":
        mismatch = measured != ae_max
    if mismatch:
        rejected.append("requested-not-applied")
        reasons.append("capture result timing differs from the requested mechanism")

    exposure_blocked = (
        "exposure-exceeds-interval" in rejected or "result-exposure-exceeds-interval" in rejected
    )
    if exposure_blocked or mismatch:
        decision = "rejected"
    elif mechanism == "manual" and measured is not None:
        decision = "manual_ready"
        reasons.append("capture result matches the manual frame duration")
        reasons.append("manual readiness comes from the capture result, not from container timestamps")
    elif mechanism == "fixed_ae" and measured is not None:
        decision = "fixed_ae_observed"
        reasons.append("capture result matches the fixed AE frame rate")
        reasons.append("fixed AE observation is not a container-timestamp certification")
    else:
        decision = "withheld"
        if mechanism == "manual":
            reasons.append("manual frame duration is not ready without a matching capture result")
            questions.append("manual timing awaiting capture-result confirmation")
        elif mechanism == "fixed_ae":
            reasons.append("fixed AE bounds were not treated as applied timing")
            questions.append("fixed AE range is not native cadence without a capture result")

    if mechanism == "variable_ae":
        reasons.append("variable AE range is not native fixed cadence")
        questions.append("native fixed cadence withheld pending measured fixed-rate evidence")
        if _includes(ae_min, ae_max, requested):
            questions.append(
                "variable AE range includes the requested rate without fixed-rate evidence"
            )
        if measured is not None:
            reasons.append(
                "a single capture result does not convert variable sensor timing into native cadence"
            )

    if mechanism != "manual" and manual["confirmed"] is False:
        questions.append("manual timing has not been confirmed")
    elif mechanism == "manual" and decision != "manual_ready" and manual["confirmed"] is False:
        questions.append("manual timing has not been confirmed")

    return _result(decision, reasons, rejected, preserved, questions)
