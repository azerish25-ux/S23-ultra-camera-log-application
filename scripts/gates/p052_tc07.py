"""TC-P052-07 denoise temporal leakage.

Intervention: Move a textured object through a region used by temporal noise
reduction.
Expected: Preserve motion and texture within the quality gate or reduce
reliance on invalid history.
Negative: Averaging unrelated frames to obtain low noise must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P052-07"
INTERVENTION = "Move a textured object through a region used by temporal noise reduction."
EXPECTED = (
    "Preserve motion and texture within the quality gate or reduce reliance on invalid history."
)
NEGATIVE = "Averaging unrelated frames to obtain low noise must fail."

_CONDITIONS = ("occlusion", "scene-cut", "low-confidence", "slow-motion")
_PAYLOAD_KEYS = (
    "condition",
    "motionPreserved",
    "texturePreserved",
    "historyReduced",
    "averagedUnrelated",
    "noise",
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
    """Keep motion and texture, or drop invalid history. Unrelated averages fail."""
    condition, motion, texture, reduced, averaged, noise = _payload(payload)
    preserved = [
        f"condition:{condition}",
        f"motion:{str(motion).lower()}",
        f"texture:{str(texture).lower()}",
        f"history-reduced:{str(reduced).lower()}",
        f"noise:{noise}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [f"{condition} noise {noise} does not replace the motion record"]
    if averaged:
        decision = "rejected"
        rejected.append("averaged-unrelated")
        reasons.append(NEGATIVE)
        questions.append("low noise from unrelated frames was rejected")
    elif (motion and texture) or reduced:
        decision = "gated"
        reasons.append("motion and texture held or invalid history was dropped")
        questions.append("gated is not a physical denoise qualification")
    else:
        decision = "rejected"
        rejected.append("temporal-leak")
        reasons.append("motion or texture was lost without dropping invalid history")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, bool, bool, bool, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    condition = payload["condition"]
    if condition not in _CONDITIONS:
        raise ValueError("condition is unsupported")
    flags = []
    for name in ("motionPreserved", "texturePreserved", "historyReduced", "averagedUnrelated"):
        value = payload[name]
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(value)
    noise = payload["noise"]
    if not isinstance(noise, str) or _DECIMAL.fullmatch(noise) is None:
        raise ValueError("noise must be a canonical decimal")
    Decimal(noise)
    return (condition, *flags, noise)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P052-07 must not yield qualified or allowed")
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
