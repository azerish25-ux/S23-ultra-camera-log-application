"""TC-P056-07 denoise temporal leakage.

Intervention: Move a textured object through a region used by temporal noise
reduction.
Expected: Preserve motion and texture within the quality gate or reduce
reliance on invalid history.
Negative: Averaging unrelated frames to obtain low noise must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P056-07"
INTERVENTION = "Move a textured object through a region used by temporal noise reduction."
EXPECTED = (
    "Preserve motion and texture within the quality gate or reduce reliance on invalid history."
)
NEGATIVE = "Averaging unrelated frames to obtain low noise must fail."

_MOTIONS = ("occlusion", "scene-cut", "low-confidence", "slow-motion")
_PAYLOAD_KEYS = (
    "motion",
    "averagedUnrelated",
    "historyInvalid",
    "texturePreserved",
    "motionPreserved",
    "relianceReduced",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Reject unrelated-frame averages. Keep motion and texture or drop bad history."""
    motion, unrelated, invalid, texture, kept_motion, reduced = _payload(payload)
    preserved = [
        f"motion:{motion}",
        f"texture:{str(texture).lower()}",
        f"motion-kept:{str(kept_motion).lower()}",
        f"history-invalid:{str(invalid).lower()}",
    ]
    rejected: list[str] = []
    questions: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"motion class {motion}"]
    if unrelated:
        decision = "rejected"
        rejected.append("unrelated-frame-average")
        reasons.append(NEGATIVE)
        questions.append("low noise from unrelated frames was not accepted")
    elif invalid and not reduced:
        decision = "rejected"
        rejected.append("invalid-history")
        reasons.append("invalid history was still used")
        questions.append(f"{motion} history was not discounted")
    elif not texture or not kept_motion:
        decision = "rejected"
        rejected.append("texture-or-motion-lost")
        reasons.append("motion or texture left the quality gate")
        questions.append("temporal filter did not keep the moving texture")
    elif invalid and reduced:
        decision = "history-limited"
        reasons.append("reliance on invalid history was reduced")
        questions.append(f"{motion} kept texture without the bad history")
    else:
        decision = "motion-kept"
        reasons.append("motion and texture stayed inside the quality gate")
        questions.append(f"{motion} did not leak across frames")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, bool, bool, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    motion = payload["motion"]
    if motion not in _MOTIONS:
        raise ValueError("motion is unsupported")
    flags = []
    for name in (
        "averagedUnrelated",
        "historyInvalid",
        "texturePreserved",
        "motionPreserved",
        "relianceReduced",
    ):
        value = payload[name]
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(value)
    return motion, flags[0], flags[1], flags[2], flags[3], flags[4]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P056-07 must not yield qualified or allowed")
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
