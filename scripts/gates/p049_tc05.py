"""TC-P049-05 false-detail enhancement.

Intervention: Increase apparent sharpness while introducing ringing, false
color, or loss of genuine fine texture.
Expected: Report each artifact separately and withhold a quality upgrade based
only on edge contrast.
Negative: A high acutance score alone must not certify recovered detail.
"""

from __future__ import annotations


CASE_ID = "TC-P049-05"
INTERVENTION = (
    "Increase apparent sharpness while introducing ringing, false color, or loss of "
    "genuine fine texture."
)
EXPECTED = (
    "Report each artifact separately and withhold a quality upgrade based only on edge "
    "contrast."
)
NEGATIVE = "A high acutance score alone must not certify recovered detail."

_SUBJECTS = ("fabric", "diagonal-lines", "point-lights", "low-light-hair")
_PAYLOAD_KEYS = (
    "subject",
    "acutance",
    "ringing",
    "falseColor",
    "textureLoss",
    "certifyFromAcutance",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Report ringing, false color, and texture loss separately. Do not upgrade."""
    subject, acutance, ringing, false_color, texture, certify = _payload(payload)
    preserved = [
        f"subject:{subject}",
        f"acutance:{acutance}",
    ]
    artifacts: list[str] = []
    if ringing:
        artifacts.append("ringing")
        preserved.append("artifact:ringing")
    if false_color:
        artifacts.append("false-color")
        preserved.append("artifact:false-color")
    if texture:
        artifacts.append("texture-loss")
        preserved.append("artifact:texture-loss")
    reasons = [EXPECTED, "edge contrast is not recovered detail"]
    if certify:
        decision = "rejected"
        rejected = ["acutance-only", *artifacts]
        reasons.append(NEGATIVE)
        questions = ["acutance score was not accepted as recovered detail"]
    else:
        decision = "withheld"
        rejected = list(artifacts)
        if artifacts:
            reasons.append("artifacts reported separately")
        questions = ["quality upgrade withheld"]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, bool, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    subject = payload["subject"]
    if subject not in _SUBJECTS:
        raise ValueError("subject is unknown")
    acutance = payload["acutance"]
    if not isinstance(acutance, str) or not acutance.isdigit() or acutance[0] == "0":
        raise ValueError("acutance must be a canonical positive integer string")
    flags = []
    for name in ("ringing", "falseColor", "textureLoss", "certifyFromAcutance"):
        if type(payload[name]) is not bool:
            raise ValueError(name + " must be a bool")
        flags.append(payload[name])
    return subject, acutance, flags[0], flags[1], flags[2], flags[3]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("decision cannot be qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
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
