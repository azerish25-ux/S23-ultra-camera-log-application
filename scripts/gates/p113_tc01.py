"""TC-P113-01 Shutter feasibility mismatch.

Host fixture. Exposure is (shutter angle / 360) / fps. A displayed angle must
not conceal a different applied exposure, and cadence is not rewritten.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P113-01"
NAME = "Shutter feasibility mismatch"
INTERVENTION = (
    "Request a shutter angle whose implied exposure conflicts with actual sensor "
    "timing or exposure limits."
)
EXPECTED = (
    "Show the effective feasible setting or reject it without silently changing source cadence."
)
NEGATIVE = "A displayed angle must not conceal a different applied exposure."
REPEAT = "Repeat integer and fractional frame rates and low-light automatic behavior."
REPEATS = ("integer-frame-rate", "fractional-frame-rate", "low-light-automatic")
NEGATIVE_TOKEN = "displayed-angle-conceals-applied-exposure"

_SPEC = importlib.util.spec_from_file_location(
    "p113_core_tc01",
    Path(__file__).resolve().parent / "p113_implement_shutter_angle_controls_correctly.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)

_PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "shutterAngleDegrees",
    "fps",
    "sensorIntervalSeconds",
    "syntheticIntegration",
    "displayedAngleDegrees",
    "appliedExposureSeconds",
    "sourceCadenceFps",
    "sensorConfirmed",
    "measurementId",
    "automaticShutterRewrite",
    "lightLimitSeconds",
)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is not a P113 shutter feasibility repeat")
    if type(payload["automaticShutterRewrite"]) is not bool:
        raise ValueError("automaticShutterRewrite must be a bool")
    if type(payload["syntheticIntegration"]) is not bool:
        raise ValueError("syntheticIntegration must be a bool")
    judge_payload = {
        "evidenceId": payload["evidenceId"],
        "shutterAngleDegrees": payload["shutterAngleDegrees"],
        "fps": payload["fps"],
        "syntheticIntegration": payload["syntheticIntegration"],
        "sensorConfirmed": payload["sensorConfirmed"],
        "measurementId": payload["measurementId"],
        "sourceCadenceFps": payload["sourceCadenceFps"],
        "reportsAngleAsApplied": payload["displayedAngleDegrees"] is not None,
    }
    if payload["sensorIntervalSeconds"] is not None:
        judge_payload["sensorIntervalSeconds"] = payload["sensorIntervalSeconds"]
    if payload["appliedExposureSeconds"] is not None:
        judge_payload["requestedExposureSeconds"] = payload["appliedExposureSeconds"]
        judge_payload["reportedExposureSeconds"] = payload["appliedExposureSeconds"]
    if payload["displayedAngleDegrees"] is not None:
        judge_payload["reportedAngleDegrees"] = payload["displayedAngleDegrees"]
    if payload["lightLimitSeconds"] is not None:
        judge_payload["sensorMaxExposureSeconds"] = payload["lightLimitSeconds"]
    result = _CORE.judge_shutter(judge_payload, CASE_ID)
    extra: list[str] = []
    reasons = [f"{CASE_ID} {NAME}", INTERVENTION, EXPECTED, f"repeat {repeat}", REPEAT]
    displayed = payload["displayedAngleDegrees"]
    applied = payload["appliedExposureSeconds"]
    if displayed is not None and applied is not None:
        matching = _CORE.exposure_seconds(displayed, payload["fps"])
        applied_value = _CORE.parse_positive(applied, "appliedExposureSeconds")
        if applied_value != matching:
            extra.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
            reasons.append(
                "effective feasible exposure for the displayed angle is "
                f"{_CORE.format_number(matching)} s; source cadence was not changed"
            )
    if payload["automaticShutterRewrite"]:
        extra.append("low-light-automatic-shutter-change")
        reasons.append(
            "low-light automatic behavior must not silently change the shutter or the cadence"
        )
    if payload["lightLimitSeconds"] is not None:
        reasons.append(
            "the light-limit tradeoff is explicit; source cadence is left unchanged"
        )
    return _CORE.reject_more(result, extra, reasons)
