"""TC-P054-05 false-detail enhancement.

Intervention: Increase apparent sharpness while introducing ringing, false
color, or loss of genuine fine texture.
Expected: Report each artifact separately and withhold a quality upgrade based
only on edge contrast.
Negative: A high acutance score alone must not certify recovered detail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P054-05"
INTERVENTION = (
    "Increase apparent sharpness while introducing ringing, false color, or loss of genuine fine texture."
)
EXPECTED = (
    "Report each artifact separately and withhold a quality upgrade based only on edge contrast."
)
NEGATIVE = "A high acutance score alone must not certify recovered detail."

_SUBJECTS = ("fabric", "diagonal", "point-light", "low-light-hair")
_PAYLOAD_KEYS = ("subject", "acutance", "ringing", "falseColor", "textureLoss", "acutanceOnly")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Report ringing, false color, and texture loss separately. Acutance is not detail."""
    subject, acutance, ringing, false_color, texture_loss, acutance_only = _payload(payload)
    preserved = [subject, f"acutance:{acutance}"]
    reasons = [EXPECTED, INTERVENTION, f"subject {subject} acutance {acutance}"]
    rejected: list[str] = []
    questions: list[str] = []
    if ringing:
        rejected.append("ringing")
        reasons.append("ringing reported separately")
    if false_color:
        rejected.append("false-color")
        reasons.append("false color reported separately")
    if texture_loss:
        rejected.append("texture-loss")
        reasons.append("genuine fine texture loss reported separately")
    if acutance_only:
        rejected.append("acutance-only")
        reasons.append(NEGATIVE)
        questions.append("acutance was not accepted as recovered detail")
    if acutance_only:
        decision = "rejected"
    elif rejected:
        decision = "withheld"
        questions.append("quality upgrade withheld; artifacts stay itemized")
    else:
        decision = "reported"
        reasons.append("no quality upgrade was claimed from edge contrast")
        questions.append(f"{subject} was inspected without a detail certificate")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, bool, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    subject = payload["subject"]
    if subject not in _SUBJECTS:
        raise ValueError("subject is unsupported")
    acutance = payload["acutance"]
    if not isinstance(acutance, str) or _DECIMAL.fullmatch(acutance) is None:
        raise ValueError("acutance must be a canonical decimal string")
    ringing = _bool(payload["ringing"], "ringing")
    false_color = _bool(payload["falseColor"], "falseColor")
    texture_loss = _bool(payload["textureLoss"], "textureLoss")
    acutance_only = _bool(payload["acutanceOnly"], "acutanceOnly")
    return subject, acutance, ringing, false_color, texture_loss, acutance_only


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P054-05 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
