"""TC-P115-01 Shutter feasibility mismatch.

Host fixture. A displayed shutter angle must not conceal a different applied
exposure, and source cadence is not silently rewritten.
"""

from __future__ import annotations

import math


CASE_ID = "TC-P115-01"
NAME = "Shutter feasibility mismatch"
INTERVENTION = (
    "Request a shutter angle whose implied exposure conflicts with actual sensor timing or exposure limits."
)
EXPECTED = "Show the effective feasible setting or reject it without silently changing source cadence."
NEGATIVE = "A displayed angle must not conceal a different applied exposure."
REPEAT = "Repeat integer and fractional frame rates and low-light automatic behavior."
TOLERANCE = 1e-9
REPEATS = ("integer-frame-rate", "fractional-frame-rate", "low-light-automatic")
PAYLOAD_KEYS = (
    "evidenceId",
    "displayedAngle",
    "appliedExposure",
    "sensorTimingExposure",
    "exposureLimit",
    "sourceCadence",
    "outputCadence",
    "repeat",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Reject a concealed exposure or a silent cadence change. Keep the feasible setting."""
    fields = _payload(payload)
    implied = fields["displayedAngle"] / 360.0
    feasible = min(fields["sensorTimingExposure"], fields["exposureLimit"])
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}"]
    if abs(implied - fields["appliedExposure"]) > TOLERANCE:
        rejected.append("displayed-angle-conceals-applied-exposure")
        reasons.append(NEGATIVE)
    if implied - fields["exposureLimit"] > TOLERANCE or fields["appliedExposure"] - fields["exposureLimit"] > TOLERANCE:
        rejected.append("exposure-limit")
        reasons.append("requested exposure exceeds the exposure limit")
    if (
        abs(implied - fields["sensorTimingExposure"]) > TOLERANCE
        or abs(fields["appliedExposure"] - fields["sensorTimingExposure"]) > TOLERANCE
    ):
        rejected.append("sensor-timing-conflict")
        reasons.append("implied exposure conflicts with sensor timing")
    if abs(fields["sourceCadence"] - fields["outputCadence"]) > TOLERANCE:
        rejected.append("source-cadence-changed")
        reasons.append("source cadence was not silently changed")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("displayed angle, applied exposure, and source cadence agree")
    preserved = [
        fields["evidenceId"],
        {
            "displayedAngle": fields["displayedAngle"],
            "impliedExposure": implied,
            "appliedExposure": fields["appliedExposure"],
            "feasibleExposure": feasible,
            "sourceCadence": fields["sourceCadence"],
            "outputCadence": fields["outputCadence"],
        },
    ]
    questions = ["physical S23 capture was not run", REPEAT]
    return _result(decision, reasons, rejected, preserved, questions)


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    displayed = _number(payload["displayedAngle"], "displayedAngle")
    applied = _number(payload["appliedExposure"], "appliedExposure")
    sensor = _number(payload["sensorTimingExposure"], "sensorTimingExposure")
    limit = _number(payload["exposureLimit"], "exposureLimit")
    source = _number(payload["sourceCadence"], "sourceCadence")
    output = _number(payload["outputCadence"], "outputCadence")
    if displayed < 0.0 or displayed > 360.0:
        raise ValueError("displayedAngle is outside 0..360")
    for label, number in (("appliedExposure", applied), ("sensorTimingExposure", sensor), ("exposureLimit", limit)):
        if number < 0.0 or number > 1.0:
            raise ValueError(f"{label} is outside 0..1")
    if source <= 0.0 or output <= 0.0:
        raise ValueError("cadence must be positive")
    if repeat == "integer-frame-rate" and (source != float(int(source)) or output != float(int(output))):
        raise ValueError("integer frame rate expected")
    if repeat == "fractional-frame-rate" and source == float(int(source)) and output == float(int(output)):
        raise ValueError("fractional frame rate expected")
    return {
        "evidenceId": evidence,
        "displayedAngle": displayed,
        "appliedExposure": applied,
        "sensorTimingExposure": sensor,
        "exposureLimit": limit,
        "sourceCadence": source,
        "outputCadence": output,
        "repeat": repeat,
    }


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or not preserved or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
