"""TC-P116-07 Guidance overrides user intent.

Host fixture. Advice may warn. It may not change a manual shutter or focus,
and it may not disable clipping warnings. Estimated frames stay origin=estimated.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

CASE_ID = "TC-P116-07"
NAME = "Guidance overrides user intent"
INTERVENTION = "Enable capture advice while the user has explicitly chosen manual exposure and focus."
EXPECTED = "Provide warnings or suggestions without hidden camera-setting changes."
NEGATIVE = "A cinematic preset that silently disables clipping warnings or changes shutter must fail."
REPEAT = "Repeat thermal advice, focus warnings, and incompatible virtual-lens framing."
NEGATIVE_TOKEN = "hidden-shutter-change"
WARNING_TOKEN = "clipping-warnings-silently-disabled"
FOCUS_TOKEN = "hidden-focus-change"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "manualExposure",
    "manualFocus",
    "adviceEnabled",
    "shutterBefore",
    "shutterAfter",
    "focusBefore",
    "focusAfter",
    "clippingWarningsBefore",
    "clippingWarningsAfter",
    "warningIssued",
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
    return math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    flags = (
        "manualExposure",
        "manualFocus",
        "adviceEnabled",
        "clippingWarningsBefore",
        "clippingWarningsAfter",
        "warningIssued",
    )
    for flag in flags:
        if type(payload[flag]) is not bool:
            raise ValueError(flag + " must be a bool")
    shutter_before = _number(payload["shutterBefore"], "shutterBefore")
    shutter_after = _number(payload["shutterAfter"], "shutterAfter")
    focus_before = _number(payload["focusBefore"], "focusBefore")
    focus_after = _number(payload["focusAfter"], "focusAfter")
    timeline = _CORE.evaluate_timeline(
        payload["captured"], payload["estimated"], payload["withheldMidpoint"]
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(timeline["reasons"])
    rejected = list(timeline["rejectedClaims"])
    if not _close(shutter_before, shutter_after):
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if payload["clippingWarningsBefore"] and not payload["clippingWarningsAfter"]:
        rejected.append(WARNING_TOKEN)
        reasons.append(NEGATIVE)
    if payload["manualFocus"] and not _close(focus_before, focus_after):
        rejected.append(FOCUS_TOKEN)
        reasons.append("manual focus must not change under advice")
    if not rejected:
        reasons.append("advice left manual shutter, focus, and clipping warnings unchanged")
        if payload["warningIssued"]:
            reasons.append("warning issued without a hidden setting change")
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
