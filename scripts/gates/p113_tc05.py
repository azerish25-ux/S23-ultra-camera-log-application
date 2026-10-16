"""TC-P113-05 Stabilization-depth misalignment.

RGB, depth, and masks share one stabilization transform. Crop changes update
the valid region and the field of view. Color-only stabilization is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P113-05"
NAME = "Stabilization-depth misalignment"
INTERVENTION = (
    "Apply a changing stabilization transform to RGB while depth begins in source coordinates."
)
EXPECTED = (
    "Transform all relevant geometry consistently and update valid region and "
    "field-of-view evidence."
)
NEGATIVE = "Stabilizing color alone while leaving masks unchanged must fail."
REPEAT = "Repeat crop changes, portrait rotation, and combined camera and subject motion."
REPEATS = ("crop-change", "portrait-rotation", "combined-motion")
NEGATIVE_TOKEN = "stabilized-color-left-masks-unchanged"

_SPEC = importlib.util.spec_from_file_location(
    "p113_core_tc05",
    Path(__file__).resolve().parent / "p113_implement_shutter_angle_controls_correctly.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)

_PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "rgbTransform",
    "depthTransform",
    "maskTransform",
    "validRegionUpdated",
    "fovUpdated",
    "cropChanged",
    "shutterAngleDegrees",
    "fps",
    "sensorConfirmed",
    "measurementId",
    "syntheticIntegration",
)


def _transform(value: object, name: str) -> tuple:
    if not isinstance(value, list) or len(value) < 4:
        raise ValueError(f"{name} must be a transform list")
    numbers = []
    for item in value:
        numbers.append(_CORE.parse_fraction(item, name))
    return tuple(numbers)


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is not a P113 stabilization repeat")
    if type(payload["syntheticIntegration"]) is not bool:
        raise ValueError("syntheticIntegration must be a bool")
    rgb = _transform(payload["rgbTransform"], "rgbTransform")
    depth = _transform(payload["depthTransform"], "depthTransform")
    mask = _transform(payload["maskTransform"], "maskTransform")
    valid = _bool(payload["validRegionUpdated"], "validRegionUpdated")
    fov = _bool(payload["fovUpdated"], "fovUpdated")
    crop = _bool(payload["cropChanged"], "cropChanged")
    result = _CORE.judge_shutter(
        {
            "evidenceId": payload["evidenceId"],
            "shutterAngleDegrees": payload["shutterAngleDegrees"],
            "fps": payload["fps"],
            "syntheticIntegration": payload["syntheticIntegration"],
            "sensorConfirmed": payload["sensorConfirmed"],
            "measurementId": payload["measurementId"],
            "reportsAngleAsApplied": True,
        },
        CASE_ID,
    )
    extra: list[str] = []
    reasons = [f"{CASE_ID} {NAME}", INTERVENTION, EXPECTED, f"repeat {repeat}", REPEAT]
    if rgb != depth or rgb != mask:
        extra.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if crop and (not valid or not fov):
        extra.append("valid-region-or-fov-stale")
        reasons.append("crop changes must update the valid region and the field of view")
    if not extra:
        reasons.append("rgb, depth, and masks share one transform")
    preserved = list(result["preservedResults"])
    preserved.append("valid-region-updated:" + str(valid).lower())
    preserved.append("fov-updated:" + str(fov).lower())
    rewritten = _CORE.finish_result(
        result["caseId"],
        result["decision"],
        result["reasons"],
        result["rejectedClaims"],
        preserved,
        result["openQuestions"],
    )
    return _CORE.reject_more(rewritten, extra, reasons)
