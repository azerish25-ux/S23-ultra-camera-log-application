"""TC-P051-05 false-detail enhancement.

Intervention: Increase apparent sharpness while introducing ringing, false
color, or loss of genuine fine texture.
Expected: Report each artifact separately and withhold a quality upgrade based
only on edge contrast.
Negative: A high acutance score alone must not certify recovered detail.
"""

from __future__ import annotations

CASE_ID = "TC-P051-05"
INTERVENTION = (
    "Increase apparent sharpness while introducing ringing, false color, or loss of genuine fine texture."
)
EXPECTED = (
    "Report each artifact separately and withhold a quality upgrade based only on edge contrast."
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
    """Withhold a sharpness upgrade. Acutance does not certify recovered detail."""
    subject, acutance, ringing, false_color, texture_loss, certify = _payload(payload)
    preserved = [f"subject:{subject}", f"acutance:{acutance}", "texture:genuine"]
    artifacts: list[str] = []
    if ringing:
        artifacts.append("ringing")
    if false_color:
        artifacts.append("false-color")
    if texture_loss:
        artifacts.append("texture-loss")
    questions = ["edge contrast is not recovered detail"]
    if certify:
        return _result(
            "rejected",
            [EXPECTED, NEGATIVE, "acutance is not recovered detail"],
            artifacts + ["acutance-certified-detail"],
            preserved,
            questions,
        )
    reasons = [EXPECTED, "quality upgrade withheld"]
    if artifacts:
        reasons.append("artifacts reported separately")
    else:
        reasons.append("no edge-contrast certificate was issued")
    return _result("withheld", reasons, artifacts, preserved, questions)


def _payload(payload: object) -> tuple[str, int, bool, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    subject = payload["subject"]
    if subject not in _SUBJECTS:
        raise ValueError("subject is not a listed repeat")
    acutance = payload["acutance"]
    if type(acutance) is not int or not 0 <= acutance <= 1000:
        raise ValueError("acutance must be an int from 0 through 1000")
    return (
        subject,
        acutance,
        _bool(payload["ringing"], "ringing"),
        _bool(payload["falseColor"], "falseColor"),
        _bool(payload["textureLoss"], "textureLoss"),
        _bool(payload["certifyFromAcutance"], "certifyFromAcutance"),
    )


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(label + " must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("detail decision cannot be qualified or allowed")
    if not reasons or any(type(item) is not str or not item for item in reasons):
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
