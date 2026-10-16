"""TC-P113-02 Existing blur ambiguity.

Qualified additional integration is allowed only when the source exposure is
shorter than the requested shutter. Existing blur cannot be removed, and an
exact arbitrary conversion is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P113-02"
NAME = "Existing blur ambiguity"
INTERVENTION = (
    "Supply sources with different amounts of already-recorded motion blur to the "
    "same synthetic-shutter request."
)
EXPECTED = (
    "Apply only qualified additional processing and identify cases that cannot be "
    "faithfully reconstructed."
)
NEGATIVE = "Claiming exact arbitrary shutter conversion from any source must fail."
REPEAT = "Repeat short exposure, long exposure, and undersampled thin motion."
REPEATS = ("short-exposure", "long-exposure", "undersampled-thin-motion")
NEGATIVE_TOKEN = "exact-arbitrary-shutter-conversion"

_SPEC = importlib.util.spec_from_file_location(
    "p113_core_tc02",
    Path(__file__).resolve().parent / "p113_implement_shutter_angle_controls_correctly.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)

_PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "sourceBlurSeconds",
    "shutterAngleDegrees",
    "fps",
    "claimExactConversion",
    "syntheticIntegration",
    "sensorConfirmed",
    "measurementId",
    "sourceCadenceFps",
)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is not a P113 existing-blur repeat")
    if type(payload["claimExactConversion"]) is not bool:
        raise ValueError("claimExactConversion must be a bool")
    if type(payload["syntheticIntegration"]) is not bool:
        raise ValueError("syntheticIntegration must be a bool")
    result = _CORE.judge_shutter(
        {
            "evidenceId": payload["evidenceId"],
            "shutterAngleDegrees": payload["shutterAngleDegrees"],
            "fps": payload["fps"],
            "syntheticIntegration": payload["syntheticIntegration"],
            "sensorConfirmed": payload["sensorConfirmed"],
            "measurementId": payload["measurementId"],
            "sourceCadenceFps": payload["sourceCadenceFps"],
            "reportsAngleAsApplied": True,
        },
        CASE_ID,
    )
    target = _CORE.exposure_seconds(payload["shutterAngleDegrees"], payload["fps"])
    source = _CORE.parse_positive(payload["sourceBlurSeconds"], "sourceBlurSeconds")
    additional = target - source
    extra: list[str] = []
    reasons = [
        f"{CASE_ID} {NAME}",
        INTERVENTION,
        EXPECTED,
        f"repeat {repeat}",
        REPEAT,
        f"source blur {_CORE.format_number(source)} s",
        f"requested shutter exposure {_CORE.format_number(target)} s",
        f"additional exposure {_CORE.format_number(additional)} s",
    ]
    if payload["claimExactConversion"]:
        extra.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if repeat == "undersampled-thin-motion":
        extra.append("cannot-faithfully-reconstruct")
        reasons.append(
            "undersampled thin motion cannot be faithfully reconstructed to the requested shutter"
        )
    elif additional <= 0:
        extra.append("cannot-faithfully-remove-blur")
        reasons.append(
            "already-recorded blur longer than or equal to the request cannot be removed"
        )
    else:
        reasons.append(
            "only qualified additional integration is applied; exact conversion is not claimed"
        )
    return _CORE.reject_more(result, extra, reasons)
