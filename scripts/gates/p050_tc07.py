"""TC-P050-07 denoise temporal leakage.

Intervention: Move a textured object through a region used by temporal noise
reduction.
Expected: Preserve motion and texture within the quality gate or reduce
reliance on invalid history.
Negative: Averaging unrelated frames to obtain low noise must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P050-07"
INTERVENTION = "Move a textured object through a region used by temporal noise reduction."
EXPECTED = (
    "Preserve motion and texture within the quality gate or reduce reliance on invalid "
    "history."
)
NEGATIVE = "Averaging unrelated frames to obtain low noise must fail."

_CONDITIONS = ("occlusion", "scene_cut", "low_confidence", "slow_motion")
_INVALID = ("occlusion", "scene_cut", "low_confidence")
_PAYLOAD_KEYS = ("condition", "averageUnrelated", "texture", "motion")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "history_reduced", "motion_kept")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep motion and texture. Unrelated-frame averages are rejected."""
    condition, average, texture, motion = _payload(payload)
    preserved = [
        f"condition:{condition}",
        f"texture:{str(texture).lower()}",
        f"motion:{str(motion).lower()}",
    ]
    if average:
        reasons = [EXPECTED, NEGATIVE, "unrelated frames were not averaged"]
        return _result(
            "rejected",
            reasons,
            ["unrelated-frame-average"],
            preserved,
            ["low noise was not purchased with invalid history"],
        )
    if not texture or not motion:
        reasons = [EXPECTED, "motion or texture left the quality gate"]
        return _result(
            "rejected",
            reasons,
            ["motion-or-texture-lost"],
            preserved,
            ["temporal history was not trusted"],
        )
    if condition in _INVALID:
        reasons = [
            EXPECTED,
            "reliance on invalid history reduced",
            f"condition:{condition}",
        ]
        return _result("history_reduced", reasons, [], preserved, [])
    reasons = [EXPECTED, "slow motion kept texture and motion", f"condition:{condition}"]
    return _result("motion_kept", reasons, [], preserved, [])


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    condition = payload["condition"]
    if condition not in _CONDITIONS:
        raise ValueError("condition must be occlusion, scene_cut, low_confidence, or slow_motion")
    flags = []
    for key in ("averageUnrelated", "texture", "motion"):
        value = payload[key]
        if type(value) is not bool:
            raise ValueError(key + " must be a bool")
        flags.append(value)
    return (condition, flags[0], flags[1], flags[2])


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("temporal decision cannot be qualified or allowed")
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
