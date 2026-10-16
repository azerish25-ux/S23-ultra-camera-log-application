"""TC-P120-01 Shutter feasibility mismatch.

Host fixture. Implied shutter exposure is (angle/360)/fps and must match the
combined report within 1e-9. A displayed angle must not conceal a different
applied exposure, and source cadence is not silently rewritten.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P120-01"
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
FPS_TOKEN = "report-fps-disagrees-with-source-cadence"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "combinationPassed",
    "report",
    "frameRate",
    "outputFrameRate",
    "requestedShutterAngleDegrees",
    "sensorMinExposureSeconds",
    "sensorMaxExposureSeconds",
)

_SPEC = importlib.util.spec_from_file_location(
    "p120_validate_combined_motion_and_optics",
    Path(__file__).resolve().parent / "p120_validate_combined_motion_and_optics.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def evaluate(payload: dict) -> dict:
    evidence, repeat = _CORE.require_payload(payload, PAYLOAD_KEYS)
    frame_rate = _CORE.require_number(payload["frameRate"], "frameRate")
    output_rate = _CORE.require_number(payload["outputFrameRate"], "outputFrameRate")
    requested = _CORE.require_number(payload["requestedShutterAngleDegrees"], "requestedShutterAngleDegrees")
    sensor_min = _CORE.require_number(payload["sensorMinExposureSeconds"], "sensorMinExposureSeconds")
    sensor_max = _CORE.require_number(payload["sensorMaxExposureSeconds"], "sensorMaxExposureSeconds")
    _CORE.require(frame_rate > 0 and output_rate > 0, "frame rate must be positive")
    _CORE.require(sensor_min >= 0 and sensor_max >= sensor_min, "sensor exposure limits are invalid")
    judgement = _CORE.judge_report(payload["report"], combination_passed=payload["combinationPassed"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(judgement["reasons"])
    rejected = list(judgement["rejectedClaims"])
    if not _CORE.exposures_match(output_rate, frame_rate):
        rejected.append(CADENCE_TOKEN)
        reasons.append("source cadence must not change silently")
    report = payload["report"] if isinstance(payload["report"], dict) else {}
    formula_holds = _CORE.EXPOSURE_MISMATCH not in rejected and _CORE.MISSING_FIELDS not in rejected
    if formula_holds:
        displayed = _CORE.require_number(report["shutter_angle"], "shutter_angle")
        applied = _CORE.require_number(report["exposure_seconds"], "exposure_seconds")
        fps = _CORE.require_number(report["fps"], "fps")
        if not _CORE.exposures_match(fps, frame_rate):
            rejected.append(FPS_TOKEN)
            reasons.append("combined report fps must keep the source cadence")
        requested_implied = _CORE.expected_exposure(requested, frame_rate)
        request_outside = (
            requested <= 0
            or requested > 360
            or requested_implied < sensor_min - _CORE.EXPOSURE_TOLERANCE
            or requested_implied > sensor_max + _CORE.EXPOSURE_TOLERANCE
        )
        feasible_max = min(360.0, sensor_max * frame_rate * 360.0)
        feasible_min = sensor_min * frame_rate * 360.0
        displayed_implied = _CORE.expected_exposure(displayed, frame_rate)
        conceals = not _CORE.exposures_match(displayed_implied, applied) or (
            not request_outside and not _CORE.exposures_match(displayed, requested)
        )
        if conceals:
            rejected.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
        honest = (
            displayed + _CORE.EXPOSURE_TOLERANCE >= feasible_min
            and displayed <= feasible_max + _CORE.EXPOSURE_TOLERANCE
            and _CORE.exposures_match(displayed_implied, applied)
        )
        applied_outside = (
            applied < sensor_min - _CORE.EXPOSURE_TOLERANCE or applied > sensor_max + _CORE.EXPOSURE_TOLERANCE
        )
        if applied_outside or (request_outside and not honest):
            rejected.append(INFEASIBLE_TOKEN)
            reasons.append("infeasible shutter rejected without changing source cadence")
        elif request_outside:
            reasons.append("effectiveFeasibleShutterAngleDegrees=" + _CORE.format_number(displayed))
            reasons.append("requested shutter was infeasible; the displayed feasible setting is retained")
        else:
            reasons.append("displayed shutter matches the applied exposure and the request")
    elif _CORE.EXPOSURE_MISMATCH in rejected:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    preserved = [evidence]
    preserved.extend(judgement["preservedResults"])
    return _CORE.assemble_result(
        case_id=CASE_ID,
        evidence=evidence,
        reasons=reasons,
        rejected=rejected,
        preserved=preserved,
        repeat_note=REPEAT,
    )
