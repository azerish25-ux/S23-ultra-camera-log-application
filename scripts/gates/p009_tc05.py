"""TC-P009-05 camera-route inventory: ambiguous timing support.

A variable AE range that merely includes the nominal rate is not fixed-cadence
evidence. Constant container timestamps must not upgrade that gap into a
native cadence, and manual timing stays uncertified until results confirm it.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P009-05"
_FIELDS = (
    "nominalFps",
    "aeRangeIncludesNominal",
    "fixedRateEvidence",
    "constantContainerTimestamps",
    "manualTimingPending",
    "rateClass",
)
_RATE_CLASSES = ("integer", "fractional")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FPS = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d+)?$")


def evaluate(payload: dict) -> dict:
    """Withhold native fixed cadence unless measured fixed-rate evidence exists."""
    data = _payload(payload)
    nominal = data["nominalFps"]
    fixed = data["fixedRateEvidence"]
    pending = data["manualTimingPending"]
    reasons = [f"{data['rateClass']} nominal {nominal} fps"]
    rejected: list[str] = []
    open_questions: list[str] = []

    if fixed and not pending:
        decision = "fixed_cadence"
        reasons.append("native fixed cadence is certified")
    else:
        decision = "withheld"
        reasons.append("native fixed cadence is not certified")

    # Container clocks are not sensor cadence. They cannot promote a withhold.
    if data["constantContainerTimestamps"] and not fixed:
        if decision in {"qualified", "allowed", "fixed_cadence"}:
            raise ValueError("constant container timestamps must not upgrade variable timing")
        rejected.append("constant-timestamps")
        reasons.append("constant container timestamps do not certify native cadence")

    if data["aeRangeIncludesNominal"] and not fixed:
        open_questions.append("variable AE range only")
    if pending:
        open_questions.append("manual timing awaiting result confirmation")

    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P009-05 must not decide qualified or allowed")
    if decision != "allowed" and not reasons:
        raise ValueError("reasons required")

    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [nominal],
        "openQuestions": open_questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_FIELDS):
        raise ValueError("invalid payload keys")
    nominal = payload["nominalFps"]
    if not isinstance(nominal, str) or _FPS.fullmatch(nominal) is None or float(nominal) <= 0:
        raise ValueError("nominalFps must be a positive numeric string")
    for key in (
        "aeRangeIncludesNominal",
        "fixedRateEvidence",
        "constantContainerTimestamps",
        "manualTimingPending",
    ):
        if not isinstance(payload[key], bool):
            raise ValueError(f"{key} must be a bool")
    if payload["rateClass"] not in _RATE_CLASSES:
        raise ValueError("rateClass must be integer or fractional")
    return payload
