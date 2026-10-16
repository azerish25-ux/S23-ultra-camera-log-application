"""TC-P118-02 Existing blur ambiguity.

Host fixture. Already recorded blur is not removed. Only non-negative additional
blur is qualified. Exact arbitrary shutter conversion is rejected. Unknown
readout still does not shift rows.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path


CASE_ID = "TC-P118-02"
NAME = "Existing blur ambiguity"
INTERVENTION = (
    "Supply sources with different amounts of already-recorded motion blur to the same synthetic-shutter request."
)
EXPECTED = "Apply only qualified additional processing and identify cases that cannot be faithfully reconstructed."
NEGATIVE = "Claiming exact arbitrary shutter conversion from any source must fail."
REPEAT = "Repeat short exposure, long exposure, and undersampled thin motion."
NEGATIVE_TOKEN = "exact-arbitrary-shutter-conversion"
CANNOT_RECONSTRUCT = "existing-blur-cannot-be-faithfully-reconstructed"
UNDERSAMPLED = "undersampled-thin-motion-cannot-be-reconstructed"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "sourceBlurSeconds",
    "targetExposureSeconds",
    "claimsExactArbitraryConversion",
    "thinMotionUndersampled",
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


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    source_blur = _number(payload["sourceBlurSeconds"], "sourceBlurSeconds")
    target = _number(payload["targetExposureSeconds"], "targetExposureSeconds")
    if source_blur < 0.0 or target < 0.0:
        raise ValueError("blur and exposure must be non-negative")
    if type(payload["claimsExactArbitraryConversion"]) is not bool:
        raise ValueError("claimsExactArbitraryConversion must be a bool")
    if type(payload["thinMotionUndersampled"]) is not bool:
        raise ValueError("thinMotionUndersampled must be a bool")
    plan = _CORE.plan_correction(
        payload["readoutSecondsPerRow"],
        payload["readoutSource"],
        payload["cameraVelocityY"],
        payload["warpLabel"],
        payload["claimsGlobalShutterRestored"],
        payload["rows"],
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    gap = target - source_blur
    if payload["claimsExactArbitraryConversion"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if source_blur > target + _CORE.ABSOLUTE_TOLERANCE:
        rejected.append(CANNOT_RECONSTRUCT)
        reasons.append("existing blur exceeds the requested exposure and is not removed")
        reasons.append("qualifiedAdditionalBlurSeconds=0")
    elif payload["thinMotionUndersampled"]:
        rejected.append(UNDERSAMPLED)
        reasons.append("undersampled thin motion cannot be faithfully reconstructed")
    else:
        reasons.append("qualifiedAdditionalBlurSeconds=" + _CORE.format_number(gap))
        if not payload["claimsExactArbitraryConversion"]:
            reasons.append("qualified additional blur only; exact arbitrary conversion is not claimed")
    reasons.extend(plan["reasons"])
    rejected.extend(plan["rejectedClaims"])
    preserved = [
        evidence,
        plan["reasons"][0],
        plan["reasons"][1],
        plan["originalY"],
        plan["yPrime"],
        plan["shiftPixels"],
        {"sourceBlurSeconds": source_blur, "targetExposureSeconds": target},
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
