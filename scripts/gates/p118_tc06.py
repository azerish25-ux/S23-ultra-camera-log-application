"""TC-P118-06 Rolling-shutter model violation.

Host fixture. Independent foreground motion blocks one global camera shear.
Advertising that shear as universal rolling-shutter removal is rejected.
Unknown readout does not shift rows. A measured correction uses
y' = y + velocity_y * row_time and reports the max row shift.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P118-06"
NAME = "Rolling-shutter model violation"
INTERVENTION = "Place independently moving foreground content in a scene used for global camera-motion correction."
EXPECTED = "Restrict or qualify the correction rather than applying an unjustified global warp to every object."
NEGATIVE = "One global shear must not be advertised as universal rolling-shutter removal."
REPEAT = "Repeat pans, vibrations, moving subjects, and unknown readout timing."
NEGATIVE_TOKEN = "global-shear-advertised-as-universal-rolling-shutter-removal"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "advertisedUniversal",
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


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    if type(payload["advertisedUniversal"]) is not bool:
        raise ValueError("advertisedUniversal must be a bool")
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
    if payload["advertisedUniversal"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    reasons.extend(plan["reasons"])
    rejected.extend(plan["rejectedClaims"])
    preserved = [
        evidence,
        plan["reasons"][0],
        plan["reasons"][1],
        plan["reasons"][2],
        plan["originalY"],
        plan["yPrime"],
        plan["shiftPixels"],
        plan["rowTimes"],
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
