"""TC-P050-05 false-detail enhancement.

Intervention: Increase apparent sharpness while introducing ringing, false
color, or loss of genuine fine texture.
Expected: Report each artifact separately and withhold a quality upgrade based
only on edge contrast.
Negative: A high acutance score alone must not certify recovered detail.
"""

from __future__ import annotations


CASE_ID = "TC-P050-05"
INTERVENTION = (
    "Increase apparent sharpness while introducing ringing, false color, or loss of "
    "genuine fine texture."
)
EXPECTED = (
    "Report each artifact separately and withhold a quality upgrade based only on "
    "edge contrast."
)
NEGATIVE = "A high acutance score alone must not certify recovered detail."

_SUBJECTS = ("fabric", "diagonal", "point_light", "hair")
_PAYLOAD_KEYS = (
    "subject",
    "ringing",
    "falseColor",
    "textureLoss",
    "acutance",
    "claimUpgrade",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld", "inspected")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Report sharpness artifacts separately. Acutance alone is not recovered detail."""
    subject, ringing, false_color, texture_loss, acutance, claim = _payload(payload)
    preserved = [
        f"subject:{subject}",
        f"acutance:{acutance}",
        f"ringing:{str(ringing).lower()}",
        f"false-color:{str(false_color).lower()}",
        f"texture-loss:{str(texture_loss).lower()}",
    ]
    artifacts: list[str] = []
    if ringing:
        artifacts.append("ringing")
    if false_color:
        artifacts.append("false-color")
    if texture_loss:
        artifacts.append("texture-loss")
    if claim:
        reasons = [EXPECTED, NEGATIVE, "quality upgrade withheld"]
        reasons.extend(f"artifact:{item}" for item in artifacts)
        return _result(
            "rejected",
            reasons,
            ["acutance-only", *artifacts],
            preserved,
            ["edge contrast is not recovered detail"],
        )
    if artifacts:
        reasons = [EXPECTED, "quality upgrade withheld"]
        reasons.extend(f"artifact:{item}" for item in artifacts)
        return _result("withheld", reasons, artifacts, preserved, ["no quality upgrade"])
    reasons = [EXPECTED, "no sharpness artifact reported", "no quality upgrade claimed"]
    return _result("inspected", reasons, [], preserved, [])


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    subject = payload["subject"]
    if subject not in _SUBJECTS:
        raise ValueError("subject must be fabric, diagonal, point_light, or hair")
    flags = []
    for key in ("ringing", "falseColor", "textureLoss", "claimUpgrade"):
        value = payload[key]
        if type(value) is not bool:
            raise ValueError(key + " must be a bool")
        flags.append(value)
    acutance = payload["acutance"]
    if type(acutance) is not int or not 0 <= acutance <= 1000:
        raise ValueError("acutance must be an int from 0 through 1000")
    return (subject, flags[0], flags[1], flags[2], acutance, flags[3])


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
