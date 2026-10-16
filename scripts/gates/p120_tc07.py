"""TC-P120-07 Guidance overrides user intent.

Host fixture. Advice may warn. It may not change a manual shutter or focus,
and it may not disable clipping warnings. The combined report keeps the
manual shutter.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P120-07"
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
    "combinationPassed",
    "report",
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
)

_SPEC = importlib.util.spec_from_file_location(
    "p120_validate_combined_motion_and_optics",
    Path(__file__).resolve().parent / "p120_validate_combined_motion_and_optics.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def evaluate(payload: dict) -> dict:
    evidence, repeat = _CORE.require_payload(payload, PAYLOAD_KEYS)
    flags = (
        "manualExposure",
        "manualFocus",
        "adviceEnabled",
        "clippingWarningsBefore",
        "clippingWarningsAfter",
        "warningIssued",
    )
    for flag in flags:
        _CORE.require(type(payload[flag]) is bool, flag + " must be a bool")
    shutter_before = _CORE.require_number(payload["shutterBefore"], "shutterBefore")
    shutter_after = _CORE.require_number(payload["shutterAfter"], "shutterAfter")
    focus_before = _CORE.require_number(payload["focusBefore"], "focusBefore")
    focus_after = _CORE.require_number(payload["focusAfter"], "focusAfter")
    judgement = _CORE.judge_report(payload["report"], combination_passed=payload["combinationPassed"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(judgement["reasons"])
    rejected = list(judgement["rejectedClaims"])
    shutter_changed = not _CORE.exposures_match(shutter_before, shutter_after)
    report_ready = _CORE.MISSING_FIELDS not in rejected and _CORE.EXPOSURE_MISMATCH not in rejected
    if report_ready and payload["manualExposure"]:
        displayed = _CORE.require_number(payload["report"]["shutter_angle"], "shutter_angle")
        if not _CORE.exposures_match(shutter_after, displayed):
            shutter_changed = True
    if shutter_changed:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if payload["clippingWarningsBefore"] and not payload["clippingWarningsAfter"]:
        rejected.append(WARNING_TOKEN)
        reasons.append(NEGATIVE)
    if payload["manualFocus"] and not _CORE.exposures_match(focus_before, focus_after):
        rejected.append(FOCUS_TOKEN)
        reasons.append("manual focus must not change under advice")
    if not rejected:
        reasons.append("advice left manual shutter, focus, and clipping warnings unchanged")
        if payload["warningIssued"]:
            reasons.append("warning issued without a hidden setting change")
    preserved = [evidence]
    preserved.extend(judgement["preservedResults"])
    return _CORE.assemble_result(
        case_id=CASE_ID,
        evidence=evidence,
        reasons=reasons,
        rejected=rejected,
        preserved=preserved,
        repeat_note=REPEAT,
    )
