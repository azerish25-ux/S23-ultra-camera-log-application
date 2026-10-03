"""TC-P051-07 denoise temporal leakage.

Intervention: Move a textured object through a region used by temporal noise
reduction.
Expected: Preserve motion and texture within the quality gate or reduce
reliance on invalid history.
Negative: Averaging unrelated frames to obtain low noise must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P051-07"
INTERVENTION = "Move a textured object through a region used by temporal noise reduction."
EXPECTED = (
    "Preserve motion and texture within the quality gate or reduce reliance on invalid history."
)
NEGATIVE = "Averaging unrelated frames to obtain low noise must fail."

_CONDITIONS = ("occlusion", "scene-cut", "low-confidence", "slow-motion")
_HISTORY = ("valid", "invalid", "unrelated")
_PAYLOAD_KEYS = ("condition", "history", "texture", "motion", "noiseScore")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "history_reduced", "motion_preserved")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep motion and texture. Do not average unrelated frames for a low noise score."""
    condition, history, texture, motion, noise = _payload(payload)
    preserved = [
        f"condition:{condition}",
        f"texture:{texture}",
        f"motion:{motion}",
        f"noise:{noise}",
    ]
    if history == "unrelated":
        return _result(
            "rejected",
            [EXPECTED, NEGATIVE, "unrelated frames were not averaged"],
            ["unrelated-frame-average"],
            preserved,
            ["low noise does not rehabilitate invalid history"],
        )
    if history == "invalid":
        return _result(
            "history_reduced",
            [EXPECTED, "reliance on invalid history reduced"],
            [],
            preserved,
            [f"{condition} history was not reused"],
        )
    return _result(
        "motion_preserved",
        [EXPECTED, "motion and texture preserved"],
        [],
        preserved,
        [],
    )


def _payload(payload: object) -> tuple[str, str, str, str, int]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    condition = payload["condition"]
    if condition not in _CONDITIONS:
        raise ValueError("condition is not a listed repeat")
    history = payload["history"]
    if history not in _HISTORY:
        raise ValueError("history must be valid, invalid, or unrelated")
    texture = _token(payload["texture"], "texture")
    motion = _token(payload["motion"], "motion")
    noise = payload["noiseScore"]
    if type(noise) is not int or not 0 <= noise <= 1000:
        raise ValueError("noiseScore must be an int from 0 through 1000")
    return condition, history, texture, motion, noise


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or any(char.isspace() for char in value):
        raise ValueError(label + " must be a single token")
    return value


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
