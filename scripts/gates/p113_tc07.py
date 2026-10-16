"""TC-P113-07 Guidance overrides user intent.

Manual exposure and focus stay under user control. Advice may warn. A preset
that changes the shutter or disables clipping warnings is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P113-07"
NAME = "Guidance overrides user intent"
INTERVENTION = (
    "Enable capture advice while the user has explicitly chosen manual exposure and focus."
)
EXPECTED = "Provide warnings or suggestions without hidden camera-setting changes."
NEGATIVE = (
    "A cinematic preset that silently disables clipping warnings or changes shutter must fail."
)
REPEAT = "Repeat thermal advice, focus warnings, and incompatible virtual-lens framing."
REPEATS = ("thermal-advice", "focus-warning", "virtual-lens-framing")
NEGATIVE_TOKEN = "preset-changed-shutter-or-disabled-clipping-warnings"

_SPEC = importlib.util.spec_from_file_location(
    "p113_core_tc07",
    Path(__file__).resolve().parent / "p113_implement_shutter_angle_controls_correctly.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)

_PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "manualExposure",
    "manualFocus",
    "adviceEnabled",
    "requestedAngleDegrees",
    "appliedAngleDegrees",
    "fps",
    "clippingWarningsEnabled",
    "clippingWarningsDisabledByPreset",
    "hiddenSettingChange",
    "warningIssued",
    "virtualLensApplied",
    "virtualLensCompatible",
    "sensorConfirmed",
    "measurementId",
    "syntheticIntegration",
)


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is not a P113 guidance repeat")
    for name in (
        "manualExposure",
        "manualFocus",
        "adviceEnabled",
        "clippingWarningsEnabled",
        "clippingWarningsDisabledByPreset",
        "hiddenSettingChange",
        "warningIssued",
        "virtualLensApplied",
        "virtualLensCompatible",
        "syntheticIntegration",
    ):
        _bool(payload[name], name)
    requested = _CORE.parse_positive(payload["requestedAngleDegrees"], "requestedAngleDegrees")
    applied = _CORE.parse_positive(payload["appliedAngleDegrees"], "appliedAngleDegrees")
    exposure = _CORE.exposure_seconds(requested, payload["fps"])
    result = _CORE.judge_shutter(
        {
            "evidenceId": payload["evidenceId"],
            "shutterAngleDegrees": payload["requestedAngleDegrees"],
            "fps": payload["fps"],
            "syntheticIntegration": payload["syntheticIntegration"],
            "sensorConfirmed": payload["sensorConfirmed"],
            "measurementId": payload["measurementId"],
            "reportedAngleDegrees": payload["requestedAngleDegrees"],
            "reportedExposureSeconds": _CORE.format_number(exposure),
            "reportsAngleAsApplied": True,
        },
        CASE_ID,
    )
    extra: list[str] = []
    reasons = [
        f"{CASE_ID} {NAME}",
        INTERVENTION,
        EXPECTED,
        f"repeat {repeat}",
        REPEAT,
        f"requested angle {_CORE.format_number(requested)} degrees stays the user shutter",
        f"user exposure {_CORE.format_number(exposure)} s",
    ]
    if applied != requested:
        extra.append(NEGATIVE_TOKEN)
        extra.append("preset-changed-shutter")
        reasons.append(NEGATIVE)
        reasons.append(
            f"applied angle {_CORE.format_number(applied)} degrees replaced the requested shutter"
        )
    if payload["clippingWarningsDisabledByPreset"] or (
        payload["adviceEnabled"] and not payload["clippingWarningsEnabled"]
    ):
        extra.append(NEGATIVE_TOKEN)
        extra.append("preset-disabled-clipping-warnings")
        reasons.append(NEGATIVE)
    if payload["hiddenSettingChange"]:
        extra.append("hidden-camera-setting-change")
        reasons.append("advice must not hide a camera-setting change")
    if payload["virtualLensApplied"] and not payload["virtualLensCompatible"]:
        extra.append("incompatible-virtual-lens-applied")
        reasons.append("an incompatible virtual lens was applied instead of warned")
    if payload["adviceEnabled"] and payload["warningIssued"] and not extra:
        reasons.append("advice issued a warning and left manual shutter and focus unchanged")
    return _CORE.reject_more(result, extra, reasons)
