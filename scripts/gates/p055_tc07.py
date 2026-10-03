"""TC-P055-07 denoise temporal leakage.

Intervention: Move a textured object through a region used by temporal noise
reduction.
Expected: Preserve motion and texture within the quality gate or reduce
reliance on invalid history.
Negative: Averaging unrelated frames to obtain low noise must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P055-07"
INTERVENTION = "Move a textured object through a region used by temporal noise reduction."
EXPECTED = (
    "Preserve motion and texture within the quality gate or reduce reliance on invalid history."
)
NEGATIVE = "Averaging unrelated frames to obtain low noise must fail."
REPEAT = "Repeat with occlusion, scene cuts, low confidence, and slow motion."

_MOTIONS = ("occlusion", "scene-cut", "low-confidence", "slow-motion", "textured")
_PAYLOAD_KEYS = (
    "subjectId",
    "textureId",
    "motion",
    "historyValid",
    "averageUnrelated",
    "noiseScore",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Keep motion and texture, or reject an average of unrelated frames."""
    subject, texture, motion, history, average, noise = _payload(payload)
    preserved = [
        f"subject:{subject}",
        f"texture:{texture}",
        f"motion:{motion}",
        f"history-valid:{str(history).lower()}",
        f"noise:{noise}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}"]
    if average:
        decision = "rejected"
        rejected = ["unrelated-frame-average"]
        reasons.append(NEGATIVE)
        questions.append(f"motion {motion} and texture {texture} were not replaced by the noise score")
    elif not history:
        decision = "history_reduced"
        rejected = []
        reasons.append(f"reliance on invalid history reduced for {motion}")
        reasons.append(f"texture {texture} preserved")
    else:
        decision = "motion_preserved"
        rejected = []
        reasons.append(f"motion {motion} and texture {texture} stay inside the quality gate")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    subject = payload["subjectId"]
    texture = payload["textureId"]
    if not isinstance(subject, str) or _TOKEN.fullmatch(subject) is None:
        raise ValueError("subjectId must be a token")
    if not isinstance(texture, str) or _TOKEN.fullmatch(texture) is None:
        raise ValueError("textureId must be a token")
    motion = payload["motion"]
    if motion not in _MOTIONS:
        raise ValueError("motion is unsupported")
    history = payload["historyValid"]
    average = payload["averageUnrelated"]
    if type(history) is not bool or type(average) is not bool:
        raise ValueError("historyValid and averageUnrelated must be bools")
    noise = payload["noiseScore"]
    if not isinstance(noise, str) or _DECIMAL.fullmatch(noise) is None:
        raise ValueError("noiseScore must be a canonical decimal string")
    return subject, texture, motion, history, average, noise


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P055-07 must not yield qualified or allowed")
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
