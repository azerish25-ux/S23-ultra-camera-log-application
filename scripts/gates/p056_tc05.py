"""TC-P056-05 false-detail enhancement.

Intervention: Increase apparent sharpness while introducing ringing, false
color, or loss of genuine fine texture.
Expected: Report each artifact separately and withhold a quality upgrade based
only on edge contrast.
Negative: A high acutance score alone must not certify recovered detail.
"""

from __future__ import annotations

import re
from fractions import Fraction


CASE_ID = "TC-P056-05"
INTERVENTION = (
    "Increase apparent sharpness while introducing ringing, false color, or loss of genuine "
    "fine texture."
)
EXPECTED = (
    "Report each artifact separately and withhold a quality upgrade based only on edge contrast."
)
NEGATIVE = "A high acutance score alone must not certify recovered detail."

_SUBJECTS = ("fabric", "diagonal-lines", "point-lights", "low-light-hair")
_PAYLOAD_KEYS = ("subject", "acutance", "ringing", "falseColor", "textureLoss")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
_HIGH = Fraction(1)


def evaluate(payload: dict) -> dict:
    """Withhold a sharpness upgrade. List ringing, false color, and texture loss apart."""
    subject, acutance, ringing, false_color, texture_loss = _payload(payload)
    preserved = [
        f"subject:{subject}",
        f"acutance:{acutance}",
        f"ringing:{str(ringing).lower()}",
        f"false-color:{str(false_color).lower()}",
        f"texture-loss:{str(texture_loss).lower()}",
    ]
    rejected: list[str] = []
    questions = ["edge contrast is not a quality upgrade"]
    reasons = [EXPECTED, INTERVENTION, f"subject {subject}"]
    if ringing:
        rejected.append("ringing")
    if false_color:
        rejected.append("false-color")
    if texture_loss:
        rejected.append("texture-loss")
    if Fraction(acutance) >= _HIGH:
        rejected.append("acutance-not-recovered-detail")
        reasons.append(NEGATIVE)
        reasons.append(f"acutance {acutance} does not certify recovered detail")
    elif not rejected:
        reasons.append("no artifact was promoted to a quality upgrade")
    decision = "withheld"
    if rejected and "acutance-not-recovered-detail" not in rejected:
        reasons.append("artifacts were reported separately")
    questions.append(f"{subject} quality upgrade withheld")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, bool, bool, bool]:
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
    flags = []
    for name in ("ringing", "falseColor", "textureLoss"):
        value = payload[name]
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(value)
    return subject, acutance, flags[0], flags[1], flags[2]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P056-05 must not yield qualified or allowed")
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
