"""TC-P117-06 Rolling-shutter model violation.

Host fixture. Expected background shear is background velocity times readout.
A single shear is not universal rolling-shutter removal. Independent
foreground motion must be excluded from that global correction. The
stabilization warp itself remains the phase translation, not this shear.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P117-06"
NAME = "Rolling-shutter model violation"
INTERVENTION = "Place independently moving foreground content in a scene used for global camera-motion correction."
EXPECTED = "Restrict or qualify the correction rather than applying an unjustified global warp to every object."
NEGATIVE = "One global shear must not be advertised as universal rolling-shutter removal."
REPEAT = "Repeat pans, vibrations, moving subjects, and unknown readout timing."
NEGATIVE_TOKEN = "global-shear-advertised-as-universal-rolling-shutter-removal"
WARP_TOKEN = "unjustified-global-warp"
READOUT_TOKEN = "unknown-readout-timing"
SHEAR_TOKEN = "shear-does-not-match-background-readout"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "foregroundVelocity",
    "backgroundVelocity",
    "globalShear",
    "readoutSeconds",
    "advertisedUniversal",
    "restrictedToBackground",
    "geometry",
)

_SPEC = importlib.util.spec_from_file_location(
    "p117_integrate_stabilization_with_geometry",
    Path(__file__).resolve().parent / "p117_integrate_stabilization_with_geometry.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def background_shear(background_velocity: float, readout_seconds: float) -> float:
    return background_velocity * readout_seconds


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    foreground = _CORE.require_number(payload["foregroundVelocity"], "foregroundVelocity")
    background = _CORE.require_number(payload["backgroundVelocity"], "backgroundVelocity")
    shear = _CORE.require_number(payload["globalShear"], "globalShear")
    readout = payload["readoutSeconds"]
    if readout is not None:
        readout = _CORE.require_number(readout, "readoutSeconds")
        if readout < 0.0:
            raise ValueError("readoutSeconds must be non-negative")
    if type(payload["advertisedUniversal"]) is not bool or type(payload["restrictedToBackground"]) is not bool:
        raise ValueError("rolling-shutter flags must be bools")
    analysis = _CORE.evaluate_geometry(payload["geometry"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(analysis["reasons"])
    rejected = list(analysis["rejectedClaims"])
    if readout is None:
        reasons.append("readout timing is unknown")
        if payload["advertisedUniversal"] or not _CORE.close(shear, 0.0):
            rejected.append(READOUT_TOKEN)
            reasons.append("unknown readout cannot justify a global shear")
        expected = None
    else:
        expected = background_shear(background, readout)
        reasons.append("expectedBackgroundShear=" + _CORE.format_number(expected))
        if not _CORE.close(shear, expected):
            rejected.append(SHEAR_TOKEN)
            reasons.append("global shear does not match background velocity times readout")
    if payload["advertisedUniversal"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if not _CORE.close(foreground, background) and not payload["restrictedToBackground"]:
        rejected.append(WARP_TOKEN)
        reasons.append("foreground motion was included in an unjustified global warp")
    elif not _CORE.close(foreground, background) and payload["restrictedToBackground"]:
        reasons.append("correction restricted to the background; foreground is not sheared with it")
    preserved = [evidence]
    if expected is not None:
        preserved.append("expectedBackgroundShear=" + _CORE.format_number(expected))
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
