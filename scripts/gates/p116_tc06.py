"""TC-P116-06 Rolling-shutter model violation.

Host fixture. A single shear is not universal rolling-shutter removal.
Independent foreground motion must be excluded from the global warp.
Estimated frames stay origin=estimated.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

CASE_ID = "TC-P116-06"
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
    "captured",
    "estimated",
    "withheldMidpoint",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p116_evaluate_interpolation_without_hidden_hallucination",
    Path(__file__).resolve().parent / "p116_evaluate_interpolation_without_hidden_hallucination.py",
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


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=_CORE.RELATIVE_TOLERANCE, abs_tol=_CORE.ABSOLUTE_TOLERANCE)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    foreground = _number(payload["foregroundVelocity"], "foregroundVelocity")
    background = _number(payload["backgroundVelocity"], "backgroundVelocity")
    shear = _number(payload["globalShear"], "globalShear")
    readout = payload["readoutSeconds"]
    if readout is not None:
        readout = _number(readout, "readoutSeconds")
        if readout < 0:
            raise ValueError("readoutSeconds must be non-negative")
    if type(payload["advertisedUniversal"]) is not bool or type(payload["restrictedToBackground"]) is not bool:
        raise ValueError("flags must be bools")
    timeline = _CORE.evaluate_timeline(
        payload["captured"], payload["estimated"], payload["withheldMidpoint"]
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(timeline["reasons"])
    rejected = list(timeline["rejectedClaims"])
    independent = not _close(foreground, background)
    if payload["advertisedUniversal"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if independent and not payload["restrictedToBackground"] and not _close(shear, 0.0):
        rejected.append(WARP_TOKEN)
        reasons.append("independent foreground motion blocks an unrestricted global shear")
    if readout is None:
        if not _close(shear, 0.0):
            rejected.append(READOUT_TOKEN)
            reasons.append("unknown readout timing cannot justify a global shear")
    else:
        expected = background * readout
        if not _close(shear, expected):
            rejected.append(SHEAR_TOKEN)
            reasons.append("expectedShear=" + format(expected, ".12g"))
        elif not payload["advertisedUniversal"]:
            scope = "background" if payload["restrictedToBackground"] or independent else "rigid-scene"
            reasons.append("shear matches " + scope + " readout model")
    preserved = [evidence]
    preserved.extend(timeline["preservedResults"])
    decision = "rejected" if rejected else "recorded"
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
