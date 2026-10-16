"""TC-P113-06 Rolling-shutter model violation.

A global shear is not universal rolling-shutter removal. Independent foreground
motion and unknown readout timing restrict the correction.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P113-06"
NAME = "Rolling-shutter model violation"
INTERVENTION = (
    "Place independently moving foreground content in a scene used for global "
    "camera-motion correction."
)
EXPECTED = (
    "Restrict or qualify the correction rather than applying an unjustified global "
    "warp to every object."
)
NEGATIVE = "One global shear must not be advertised as universal rolling-shutter removal."
REPEAT = "Repeat pans, vibrations, moving subjects, and unknown readout timing."
REPEATS = ("pans", "vibrations", "moving-subjects", "unknown-readout")
NEGATIVE_TOKEN = "global-shear-as-universal-rolling-shutter-removal"

_SPEC = importlib.util.spec_from_file_location(
    "p113_core_tc06",
    Path(__file__).resolve().parent / "p113_implement_shutter_angle_controls_correctly.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)

_PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "independentForegroundMotion",
    "globalShearApplied",
    "advertisedAsUniversalRemoval",
    "readoutTimingKnown",
    "correctionRestricted",
    "shutterAngleDegrees",
    "fps",
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
        raise ValueError("repeat is not a P113 rolling-shutter repeat")
    if type(payload["syntheticIntegration"]) is not bool:
        raise ValueError("syntheticIntegration must be a bool")
    independent = _bool(payload["independentForegroundMotion"], "independentForegroundMotion")
    shear = _bool(payload["globalShearApplied"], "globalShearApplied")
    universal = _bool(payload["advertisedAsUniversalRemoval"], "advertisedAsUniversalRemoval")
    known = _bool(payload["readoutTimingKnown"], "readoutTimingKnown")
    restricted = _bool(payload["correctionRestricted"], "correctionRestricted")
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
    if universal:
        extra.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if independent and shear and not restricted:
        extra.append("unjustified-global-warp")
        reasons.append(
            "independent foreground motion forbids an unrestricted global warp"
        )
    if (not known) and shear:
        extra.append("unknown-readout-global-shear")
        reasons.append("unknown readout timing cannot support a global shear")
    if repeat == "unknown-readout" and not known and not restricted:
        extra.append("unknown-readout-unqualified")
        reasons.append("unknown readout timing restricts the correction")
    if not extra:
        reasons.append("the correction stayed restricted and was not called universal")
    return _CORE.reject_more(result, extra, reasons)
