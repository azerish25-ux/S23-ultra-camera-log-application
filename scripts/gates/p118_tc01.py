"""TC-P118-01 Shutter feasibility mismatch.

Host fixture. A displayed shutter angle must not conceal a different applied
exposure, and source cadence is not silently rewritten. Row shifts still follow
the measured-readout rule: unknown readout does not move rows.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path


CASE_ID = "TC-P118-01"
NAME = "Shutter feasibility mismatch"
INTERVENTION = (
    "Request a shutter angle whose implied exposure conflicts with actual sensor timing or exposure limits."
)
EXPECTED = "Show the effective feasible setting or reject it without silently changing source cadence."
NEGATIVE = "A displayed angle must not conceal a different applied exposure."
REPEAT = "Repeat integer and fractional frame rates and low-light automatic behavior."
NEGATIVE_TOKEN = "displayed-angle-conceals-applied-exposure"
LIMIT_TOKEN = "exposure-limit"
CADENCE_TOKEN = "source-cadence-changed"
CONFLICT_TOKEN = "sensor-timing-conflict"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "displayedAngle",
    "appliedExposure",
    "sensorTimingExposure",
    "exposureLimit",
    "sourceCadence",
    "outputCadence",
    "readoutSecondsPerRow",
    "readoutSource",
    "cameraVelocityY",
    "warpLabel",
    "claimsGlobalShutterRestored",
    "rows",
)

_SPEC = importlib.util.spec_from_file_location(
    "p118_investigate_rolling_shutter_correction_conservatively",
    Path(__file__).resolve().parent / "p118_investigate_rolling_shutter_correction_conservatively.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _number(value, label: str) -> float:
    if type(value) is bool or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=_CORE.RELATIVE_TOLERANCE, abs_tol=_CORE.ABSOLUTE_TOLERANCE)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    displayed = _number(payload["displayedAngle"], "displayedAngle")
    applied = _number(payload["appliedExposure"], "appliedExposure")
    sensor = _number(payload["sensorTimingExposure"], "sensorTimingExposure")
    limit = _number(payload["exposureLimit"], "exposureLimit")
    source = _number(payload["sourceCadence"], "sourceCadence")
    output = _number(payload["outputCadence"], "outputCadence")
    if displayed < 0.0 or displayed > 360.0:
        raise ValueError("displayedAngle is outside 0..360")
    if source <= 0.0 or output <= 0.0:
        raise ValueError("cadence must be positive")
    if min(applied, sensor, limit) < 0.0:
        raise ValueError("exposure must be non-negative")
    plan = _CORE.plan_correction(
        payload["readoutSecondsPerRow"],
        payload["readoutSource"],
        payload["cameraVelocityY"],
        payload["warpLabel"],
        payload["claimsGlobalShutterRestored"],
        payload["rows"],
    )
    implied = (displayed / 360.0) / source
    feasible = min(sensor, limit)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if not _close(implied, applied):
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if applied - limit > _CORE.ABSOLUTE_TOLERANCE or applied - sensor > _CORE.ABSOLUTE_TOLERANCE:
        rejected.append(LIMIT_TOKEN)
        reasons.append("requested exposure exceeds the exposure limit")
    if implied - feasible > _CORE.ABSOLUTE_TOLERANCE or applied - feasible > _CORE.ABSOLUTE_TOLERANCE:
        rejected.append(CONFLICT_TOKEN)
        reasons.append("implied exposure conflicts with sensor timing")
    if not _close(source, output):
        rejected.append(CADENCE_TOKEN)
        reasons.append("source cadence was not silently changed")
    reasons.append("effectiveFeasibleExposureSeconds=" + _CORE.format_number(feasible))
    if not rejected:
        reasons.append("displayed angle, applied exposure, and source cadence agree")
    reasons.extend(plan["reasons"])
    rejected.extend(plan["rejectedClaims"])
    preserved = [
        evidence,
        plan["reasons"][0],
        plan["reasons"][1],
        plan["originalY"],
        plan["yPrime"],
        plan["shiftPixels"],
        {
            "displayedAngle": displayed,
            "impliedExposure": implied,
            "appliedExposure": applied,
            "feasibleExposure": feasible,
            "sourceCadence": source,
            "outputCadence": output,
        },
    ]
    decision = "rejected" if rejected else "recorded"
    return _CORE.case_result(
        CASE_ID,
        decision,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
