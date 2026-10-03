"""TC-P054-07 denoise temporal leakage.

Intervention: Move a textured object through a region used by temporal noise
reduction.
Expected: Preserve motion and texture within the quality gate or reduce
reliance on invalid history.
Negative: Averaging unrelated frames to obtain low noise must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P054-07"
INTERVENTION = "Move a textured object through a region used by temporal noise reduction."
EXPECTED = (
    "Preserve motion and texture within the quality gate or reduce reliance on invalid history."
)
NEGATIVE = "Averaging unrelated frames to obtain low noise must fail."

_MOTIONS = ("occlusion", "scene-cut", "low-confidence", "slow-motion", "textured-pass")
_INVALID_HISTORY = {"occlusion", "scene-cut", "low-confidence"}
_TEXTURE_FLOOR = Decimal("0.85")
_PAYLOAD_KEYS = (
    "motion",
    "historyValid",
    "textureRetention",
    "motionTrail",
    "qualityGate",
    "averagedUnrelated",
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
    """Keep motion inside the trail gate, or drop invalid temporal history."""
    motion, history_valid, texture, trail, gate, averaged = _payload(payload)
    preserved = [
        motion,
        f"texture:{texture}",
        f"trail:{trail}",
        f"gate:{gate}",
        "history:valid" if history_valid else "history:invalid",
    ]
    reasons = [EXPECTED, INTERVENTION, f"motion {motion} texture {texture} trail {trail}"]
    rejected: list[str] = []
    questions: list[str] = []
    if averaged:
        decision = "rejected"
        rejected.append("unrelated-frame-average")
        reasons.append(NEGATIVE)
        questions.append("unrelated-frame average was rejected; texture and trail stay recorded")
        return _result(decision, reasons, rejected, preserved, questions)
    if Decimal(trail) > Decimal(gate):
        rejected.append("temporal-leakage")
        reasons.append("motion trail exceeds the declared quality gate")
    if Decimal(texture) < _TEXTURE_FLOOR:
        rejected.append("texture-smear")
        reasons.append("texture retention is below 0.85")
    if rejected:
        decision = "rejected"
        questions.append("temporal failure did not erase the motion class")
    elif motion in _INVALID_HISTORY or not history_valid:
        decision = "history-reduced"
        reasons.append("reliance on invalid history was reduced")
        questions.append(f"{motion} did not keep an invalid temporal history")
    else:
        decision = "motion-preserved"
        reasons.append("motion and texture stayed inside the quality gate")
        questions.append(f"{motion} preserved within gate {gate}")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, bool, str, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    motion = payload["motion"]
    if motion not in _MOTIONS:
        raise ValueError("motion is unsupported")
    history_valid = payload["historyValid"]
    if type(history_valid) is not bool:
        raise ValueError("historyValid must be a bool")
    texture = _decimal(payload["textureRetention"], "textureRetention")
    trail = _decimal(payload["motionTrail"], "motionTrail")
    gate = _decimal(payload["qualityGate"], "qualityGate")
    if Decimal(gate) <= 0:
        raise ValueError("qualityGate must be positive")
    averaged = payload["averagedUnrelated"]
    if type(averaged) is not bool:
        raise ValueError("averagedUnrelated must be a bool")
    return motion, history_valid, texture, trail, gate, averaged


def _decimal(value: object, label: str) -> str:
    if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
        raise ValueError(f"{label} must be a canonical decimal string")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P054-07 must not yield qualified or allowed")
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
