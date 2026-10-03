"""TC-P049-07 denoise temporal leakage.

Intervention: Move a textured object through a region used by temporal noise
reduction.
Expected: Preserve motion and texture within the quality gate or reduce
reliance on invalid history.
Negative: Averaging unrelated frames to obtain low noise must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P049-07"
INTERVENTION = "Move a textured object through a region used by temporal noise reduction."
EXPECTED = (
    "Preserve motion and texture within the quality gate or reduce reliance on invalid "
    "history."
)
NEGATIVE = "Averaging unrelated frames to obtain low noise must fail."

_CONDITIONS = ("occlusion", "scene-cut", "low-confidence", "slow-motion", "steady")
_HISTORY = ("occlusion", "scene-cut", "low-confidence")
_PAYLOAD_KEYS = ("condition", "motion", "texture", "averageUnrelated")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "history_reduced", "texture_preserved")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep motion and texture. Unrelated-frame averages fail."""
    condition, motion, texture, average = _payload(payload)
    preserved = [
        f"condition:{condition}",
        f"motion:{str(motion).lower()}",
        f"texture:{str(texture).lower()}",
    ]
    reasons = [EXPECTED]
    if average:
        decision = "rejected"
        rejected = ["unrelated-frame-average"]
        reasons.append(NEGATIVE)
        questions = ["motion and texture inventory kept after the average was rejected"]
    elif condition in _HISTORY:
        decision = "history_reduced"
        rejected = []
        reasons.append("reliance on invalid history reduced")
        questions = [f"{condition} did not license an unrelated average"]
    else:
        decision = "texture_preserved"
        rejected = []
        reasons.append("motion and texture preserved")
        questions = ["temporal gate did not replace the textured object"]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    condition = payload["condition"]
    if condition not in _CONDITIONS:
        raise ValueError("condition is unknown")
    flags = []
    for name in ("motion", "texture", "averageUnrelated"):
        if type(payload[name]) is not bool:
            raise ValueError(name + " must be a bool")
        flags.append(payload[name])
    return condition, flags[0], flags[1], flags[2]


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
