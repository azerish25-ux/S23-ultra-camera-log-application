"""TC-P055-05 false-detail enhancement.

Intervention: Increase apparent sharpness while introducing ringing, false
color, or loss of genuine fine texture.
Expected: Report each artifact separately and withhold a quality upgrade based
only on edge contrast.
Negative: A high acutance score alone must not certify recovered detail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P055-05"
INTERVENTION = (
    "Increase apparent sharpness while introducing ringing, false color, or loss of "
    "genuine fine texture."
)
EXPECTED = (
    "Report each artifact separately and withhold a quality upgrade based only on edge contrast."
)
NEGATIVE = "A high acutance score alone must not certify recovered detail."
REPEAT = "Repeat with fabric, diagonal lines, point lights, and low-light hair."

_SUBJECTS = ("fabric", "diagonal-lines", "point-lights", "low-light-hair")
_PAYLOAD_KEYS = (
    "subject",
    "acutance",
    "ringing",
    "falseColor",
    "textureLoss",
    "edgeContrastOnly",
)
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
    """Report sharpening artifacts separately and withhold an acutance upgrade."""
    subject, acutance, ringing, false_color, texture_loss, edge_only = _payload(payload)
    artifacts: list[str] = []
    if ringing:
        artifacts.append("ringing")
    if false_color:
        artifacts.append("false-color")
    if texture_loss:
        artifacts.append("texture-loss")
    preserved = [
        f"subject:{subject}",
        f"acutance:{acutance}",
        f"ringing:{str(ringing).lower()}",
        f"false-color:{str(false_color).lower()}",
        f"texture-loss:{str(texture_loss).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}"]
    rejected = list(artifacts)
    for name in artifacts:
        reasons.append(f"artifact {name} reported separately")
    if edge_only or artifacts:
        decision = "withheld"
        if edge_only:
            rejected.append("acutance-only")
            reasons.append(NEGATIVE)
            questions.append(f"acutance {acutance} did not certify recovered detail")
        else:
            questions.append("quality upgrade withheld")
    else:
        decision = "recorded"
        reasons.append("no quality upgrade was certified")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
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
    for name in ("ringing", "falseColor", "textureLoss", "edgeContrastOnly"):
        if type(payload[name]) is not bool:
            raise ValueError(name + " must be a bool")
        flags.append(payload[name])
    return (subject, acutance, *flags)


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P055-05 must not yield qualified or allowed")
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
