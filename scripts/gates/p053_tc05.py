"""TC-P053-05 false-detail enhancement.

Intervention: Increase apparent sharpness while introducing ringing, false
color, or loss of genuine fine texture.
Expected: Report each artifact separately and withhold a quality upgrade based
only on edge contrast.
Negative: A high acutance score alone must not certify recovered detail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P053-05"
INTERVENTION = (
    "Increase apparent sharpness while introducing ringing, false color, or loss of "
    "genuine fine texture."
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
_DECISIONS = ("rejected", "withheld")
_FORBIDDEN = {"qualified", "allowed"}
_UINT = re.compile(r"0|[1-9][0-9]*")
_HIGH = 50


def evaluate(payload: dict) -> dict:
    """Report sharpness artifacts separately. Acutance does not certify detail."""
    subject, acutance, ringing, false_color, texture_loss, edge_only = _payload(payload)
    preserved = [
        f"subject:{subject}",
        f"acutance:{acutance}",
        f"edge-contrast-only:{str(edge_only).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    artifacts: list[str] = []
    if ringing:
        artifacts.append("ringing")
    if false_color:
        artifacts.append("false-color")
    if texture_loss:
        artifacts.append("texture-loss")
    if edge_only or int(acutance) >= _HIGH:
        reasons.append(NEGATIVE)
    if edge_only:
        return _result(
            "rejected",
            reasons,
            ["acutance-only", *artifacts],
            preserved,
            ["edge contrast is not recovered detail"],
        )
    if artifacts:
        reasons.append("artifacts reported separately; no quality upgrade")
        return _result(
            "withheld",
            reasons,
            artifacts,
            preserved,
            ["quality upgrade withheld"],
        )
    reasons.append("no artifact was declared; acutance still does not certify detail")
    return _result(
        "withheld",
        reasons,
        [],
        preserved,
        ["acutance is not recovered detail"],
    )


def _payload(payload: object) -> tuple[str, str, bool, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    subject = payload["subject"]
    if subject not in _SUBJECTS:
        raise ValueError("subject is unknown")
    acutance = payload["acutance"]
    if not isinstance(acutance, str) or _UINT.fullmatch(acutance) is None:
        raise ValueError("acutance must be a canonical non-negative integer string")
    flags = (payload["ringing"], payload["falseColor"], payload["textureLoss"], payload["edgeContrastOnly"])
    if any(type(item) is not bool for item in flags):
        raise ValueError("artifact flags must be bools")
    return subject, acutance, flags[0], flags[1], flags[2], flags[3]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("detail decision cannot be qualified or allowed")
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
