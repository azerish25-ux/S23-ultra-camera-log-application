"""TC-P116-01 Shutter feasibility mismatch.

Host fixture. Implied shutter exposure is checked against sensor limits.
A displayed angle must not conceal a different applied exposure, and source
cadence is not silently rewritten. Estimated frames stay origin=estimated.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

CASE_ID = "TC-P116-01"
NAME = "Shutter feasibility mismatch"
INTERVENTION = (
    "Request a shutter angle whose implied exposure conflicts with actual sensor timing or exposure limits."
)
EXPECTED = "Show the effective feasible setting or reject it without silently changing source cadence."
NEGATIVE = "A displayed angle must not conceal a different applied exposure."
REPEAT = "Repeat integer and fractional frame rates and low-light automatic behavior."
NEGATIVE_TOKEN = "displayed-angle-conceals-applied-exposure"
INFEASIBLE_TOKEN = "shutter-infeasible"
CADENCE_TOKEN = "silent-source-cadence-change"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "frameRate",
    "outputFrameRate",
    "shutterAngleDegrees",
    "displayedShutterAngleDegrees",
    "appliedExposureSeconds",
    "sensorMinExposureSeconds",
    "sensorMaxExposureSeconds",
    "captured",
    "estimated",
    "withheldMidpoint",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p116_evaluate_interpolation_without_hidden_hallucination",
    Path(__file__).resolve().parent / "p116_evaluate_interpolation_without_hidden_hallucination.py",
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


def _exposure(angle_degrees: float, frame_rate: float) -> float:
    return (angle_degrees / 360.0) / frame_rate


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-12)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    frame_rate = _number(payload["frameRate"], "frameRate")
    output_rate = _number(payload["outputFrameRate"], "outputFrameRate")
    requested = _number(payload["shutterAngleDegrees"], "shutterAngleDegrees")
    displayed = _number(payload["displayedShutterAngleDegrees"], "displayedShutterAngleDegrees")
    applied = _number(payload["appliedExposureSeconds"], "appliedExposureSeconds")
    sensor_min = _number(payload["sensorMinExposureSeconds"], "sensorMinExposureSeconds")
    sensor_max = _number(payload["sensorMaxExposureSeconds"], "sensorMaxExposureSeconds")
    if frame_rate <= 0 or output_rate <= 0:
        raise ValueError("frame rate must be positive")
    if sensor_min < 0 or sensor_max < sensor_min:
        raise ValueError("sensor exposure limits are invalid")
    timeline = _CORE.evaluate_timeline(
        payload["captured"], payload["estimated"], payload["withheldMidpoint"]
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(timeline["reasons"])
    rejected = list(timeline["rejectedClaims"])
    displayed_implied = _exposure(displayed, frame_rate)
    requested_implied = _exposure(requested, frame_rate)
    request_outside = (
        requested_implied < sensor_min - 1e-12
        or requested_implied > sensor_max + 1e-12
        or requested <= 0
        or requested > 360
    )
    conceals = not _close(displayed_implied, applied) or (
        not request_outside and not _close(displayed, requested)
    )
    if conceals:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if not _close(output_rate, frame_rate):
        rejected.append(CADENCE_TOKEN)
        reasons.append("source cadence must not change silently")
    feasible_max_angle = min(360.0, sensor_max * frame_rate * 360.0)
    feasible_min_angle = sensor_min * frame_rate * 360.0
    applied_outside = applied < sensor_min - 1e-12 or applied > sensor_max + 1e-12
    honest_feasible = (
        feasible_min_angle - 1e-9 <= displayed <= feasible_max_angle + 1e-9
        and _close(displayed_implied, applied)
    )
    if applied_outside or (request_outside and not honest_feasible):
        rejected.append(INFEASIBLE_TOKEN)
        reasons.append(
            "effectiveFeasibleShutterAngleDegrees="
            + format(min(max(displayed, feasible_min_angle), feasible_max_angle), ".12g")
        )
        reasons.append("infeasible shutter rejected without changing source cadence")
    elif request_outside:
        reasons.append(
            "effectiveFeasibleShutterAngleDegrees=" + format(displayed, ".12g")
        )
        reasons.append("requested shutter was infeasible; the displayed feasible setting is retained")
    preserved = [evidence]
    preserved.extend(timeline["preservedResults"])
    decision = "rejected" if rejected else "recorded"
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
