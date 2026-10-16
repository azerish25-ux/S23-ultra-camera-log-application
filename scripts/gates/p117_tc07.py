"""TC-P117-07 Guidance overrides user intent.

Host fixture. Advice may warn. It may not change a manual shutter or focus,
and it may not disable clipping warnings. Stabilization geometry is still
judged by the phase crop contract, including virtual-lens aspect changes.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P117-07"
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
    "shutterBefore",
    "shutterAfter",
    "focusBefore",
    "focusAfter",
    "clippingWarningsBefore",
    "clippingWarningsAfter",
    "warningIssued",
    "geometry",
)

_SPEC = importlib.util.spec_from_file_location(
    "p117_integrate_stabilization_with_geometry",
    Path(__file__).resolve().parent / "p117_integrate_stabilization_with_geometry.py",
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
    for name in ("manualExposure", "manualFocus", "clippingWarningsBefore", "clippingWarningsAfter", "warningIssued"):
        if type(payload[name]) is not bool:
            raise ValueError(name + " must be a bool")
    shutter_before = _CORE.require_number(payload["shutterBefore"], "shutterBefore")
    shutter_after = _CORE.require_number(payload["shutterAfter"], "shutterAfter")
    focus_before = _CORE.require_number(payload["focusBefore"], "focusBefore")
    focus_after = _CORE.require_number(payload["focusAfter"], "focusAfter")
    if shutter_before <= 0.0 or shutter_after <= 0.0:
        raise ValueError("shutter angles must be positive")
    if focus_before <= 0.0 or focus_after <= 0.0:
        raise ValueError("focus distances must be positive")
    analysis = _CORE.evaluate_geometry(payload["geometry"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(analysis["reasons"])
    rejected = list(analysis["rejectedClaims"])
    if payload["manualExposure"] and not _CORE.close(shutter_before, shutter_after):
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append(
            "shutter changed from "
            + _CORE.format_number(shutter_before)
            + " to "
            + _CORE.format_number(shutter_after)
        )
    if payload["manualFocus"] and not _CORE.close(focus_before, focus_after):
        rejected.append(FOCUS_TOKEN)
        reasons.append("manual focus changed under capture advice")
    if payload["clippingWarningsBefore"] and not payload["clippingWarningsAfter"]:
        rejected.append(WARNING_TOKEN)
        reasons.append("clipping warnings were disabled without a user action")
    if payload["warningIssued"] and not rejected:
        reasons.append("advice issued a warning and left manual shutter and focus unchanged")
    preserved = [
        evidence,
        "shutter=" + _CORE.format_number(shutter_before) + "->" + _CORE.format_number(shutter_after),
        "focus=" + _CORE.format_number(focus_before) + "->" + _CORE.format_number(focus_after),
    ]
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
