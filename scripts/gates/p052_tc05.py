"""TC-P052-05 false-detail enhancement.

Intervention: Increase apparent sharpness while introducing ringing, false
color, or loss of genuine fine texture.
Expected: Report each artifact separately and withhold a quality upgrade based
only on edge contrast.
Negative: A high acutance score alone must not certify recovered detail.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P052-05"
INTERVENTION = (
    "Increase apparent sharpness while introducing ringing, false color, or loss of genuine fine texture."
)
EXPECTED = (
    "Report each artifact separately and withhold a quality upgrade based only on edge contrast."
)
NEGATIVE = "A high acutance score alone must not certify recovered detail."

_SCENES = ("fabric", "diagonal", "point-lights", "hair")
_PAYLOAD_KEYS = ("scene", "acutance", "ringing", "falseColor", "textureLoss", "acutanceOnly")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
_LIMIT = Decimal("0.02")


def evaluate(payload: dict) -> dict:
    """Itemize ringing, false color, and texture loss. Acutance does not certify."""
    scene, acutance, ringing, false_color, texture, acutance_only = _payload(payload)
    preserved = [
        f"scene:{scene}",
        f"acutance:{acutance}",
        f"ringing:{ringing}",
        f"false-color:{false_color}",
        f"texture-loss:{texture}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = ["artifacts were stored separately from acutance"]
    artifacts = (
        ("ringing", Decimal(ringing)),
        ("false-color", Decimal(false_color)),
        ("texture-loss", Decimal(texture)),
    )
    for name, number in artifacts:
        if number > _LIMIT:
            rejected.append(name)
            reasons.append(f"{name} { _canon(number) } reported separately")
    if acutance_only:
        decision = "rejected"
        rejected.insert(0, "acutance-only")
        reasons.append(NEGATIVE)
        questions.append("acutance did not certify recovered detail")
    elif rejected:
        decision = "withheld"
        reasons.append("quality upgrade withheld; edge contrast is not recovered detail")
        questions.append(f"{scene} upgrade withheld")
    else:
        decision = "reported"
        reasons.append("no artifact exceeded the host threshold; acutance still does not certify detail")
        questions.append("reported is not a measured detail recovery")
    return _result(decision, reasons, rejected, preserved, questions)


def _canon(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _payload(payload: object) -> tuple[str, str, str, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    scene = payload["scene"]
    if scene not in _SCENES:
        raise ValueError("scene is unsupported")
    numbers = []
    for name in ("acutance", "ringing", "falseColor", "textureLoss"):
        value = payload[name]
        if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
            raise ValueError(f"{name} must be a canonical decimal")
        numbers.append(value)
    acutance_only = payload["acutanceOnly"]
    if type(acutance_only) is not bool:
        raise ValueError("acutanceOnly must be a bool")
    return (scene, *numbers, acutance_only)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P052-05 must not yield qualified or allowed")
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
