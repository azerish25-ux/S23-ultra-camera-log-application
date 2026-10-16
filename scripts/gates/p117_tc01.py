"""TC-P117-01 Shutter feasibility mismatch.

Host fixture. Implied shutter exposure is checked against sensor limits.
A displayed angle must not conceal a different applied exposure, and source
cadence is not silently rewritten. Stabilization geometry is evaluated with
the same crop and translation contract as the phase gate.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P117-01"
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
SILENT_SHUTTER_TOKEN = "silent-shutter-change"
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
    "geometry",
)

_SPEC = importlib.util.spec_from_file_location(
    "p117_integrate_stabilization_with_geometry",
    Path(__file__).resolve().parent / "p117_integrate_stabilization_with_geometry.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def exposure_seconds(angle_degrees: float, frame_rate: float) -> float:
    """Exposure implied by a shutter angle at the source frame rate. Cadence is not rewritten."""
    return (angle_degrees / 360.0) / frame_rate


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    frame_rate = _CORE.require_number(payload["frameRate"], "frameRate")
    output_rate = _CORE.require_number(payload["outputFrameRate"], "outputFrameRate")
    requested = _CORE.require_number(payload["shutterAngleDegrees"], "shutterAngleDegrees")
    displayed = _CORE.require_number(payload["displayedShutterAngleDegrees"], "displayedShutterAngleDegrees")
    applied = _CORE.require_number(payload["appliedExposureSeconds"], "appliedExposureSeconds")
    sensor_min = _CORE.require_number(payload["sensorMinExposureSeconds"], "sensorMinExposureSeconds")
    sensor_max = _CORE.require_number(payload["sensorMaxExposureSeconds"], "sensorMaxExposureSeconds")
    if frame_rate <= 0.0 or output_rate <= 0.0:
        raise ValueError("frame rate must be positive")
    if requested <= 0.0 or requested > 360.0 or displayed <= 0.0 or displayed > 360.0:
        raise ValueError("shutter angle must be in (0, 360]")
    if sensor_min < 0.0 or sensor_max < sensor_min:
        raise ValueError("sensor exposure limits are invalid")
    analysis = _CORE.evaluate_geometry(payload["geometry"])
    requested_exposure = exposure_seconds(requested, frame_rate)
    displayed_exposure = exposure_seconds(displayed, frame_rate)
    feasible_exposure = min(max(requested_exposure, sensor_min), sensor_max)
    feasible_angle = feasible_exposure * frame_rate * 360.0
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(analysis["reasons"])
    reasons.append(
        "impliedDisplayedExposureSeconds="
        + _CORE.format_number(displayed_exposure)
        + " appliedExposureSeconds="
        + _CORE.format_number(applied)
        + " feasibleExposureSeconds="
        + _CORE.format_number(feasible_exposure)
    )
    rejected = list(analysis["rejectedClaims"])
    if not _CORE.close(displayed_exposure, applied):
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if not _CORE.close(output_rate, frame_rate):
        rejected.append(CADENCE_TOKEN)
        reasons.append("source cadence must not change silently")
    request_outside = (
        requested_exposure < sensor_min - _CORE.ABSOLUTE_TOLERANCE
        or requested_exposure > sensor_max + _CORE.ABSOLUTE_TOLERANCE
    )
    applied_outside = (
        applied < sensor_min - _CORE.ABSOLUTE_TOLERANCE
        or applied > sensor_max + _CORE.ABSOLUTE_TOLERANCE
    )
    displayed_outside = (
        displayed_exposure < sensor_min - _CORE.ABSOLUTE_TOLERANCE
        or displayed_exposure > sensor_max + _CORE.ABSOLUTE_TOLERANCE
    )
    if request_outside or applied_outside or displayed_outside:
        honest = (
            _CORE.close(applied, feasible_exposure)
            and _CORE.close(displayed_exposure, feasible_exposure)
            and not applied_outside
        )
        if honest:
            reasons.append(
                "effectiveFeasibleShutterAngleDegrees=" + _CORE.format_number(feasible_angle)
            )
            reasons.append("infeasible shutter replaced by the feasible setting without changing source cadence")
        else:
            rejected.append(INFEASIBLE_TOKEN)
            reasons.append(
                "effectiveFeasibleShutterAngleDegrees=" + _CORE.format_number(feasible_angle)
            )
            reasons.append("infeasible shutter rejected without changing source cadence")
    elif not _CORE.close(displayed, requested):
        rejected.append(SILENT_SHUTTER_TOKEN)
        reasons.append("feasible requested shutter was changed without saying so")
    preserved = [evidence]
    preserved.extend(analysis["preservedResults"])
    decision = "rejected" if rejected else "recorded"
    return _CORE.seal_result(
        CASE_ID,
        decision,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
