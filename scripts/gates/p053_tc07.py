"""TC-P053-07 denoise temporal leakage.

Intervention: Move a textured object through a region used by temporal noise
reduction.
Expected: Preserve motion and texture within the quality gate or reduce
reliance on invalid history.
Negative: Averaging unrelated frames to obtain low noise must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P053-07"
INTERVENTION = "Move a textured object through a region used by temporal noise reduction."
EXPECTED = (
    "Preserve motion and texture within the quality gate or reduce reliance on invalid history."
)
NEGATIVE = "Averaging unrelated frames to obtain low noise must fail."

_EVENTS = ("occlusion", "scene-cut", "low-confidence", "slow-motion")
_PAYLOAD_KEYS = (
    "event",
    "regionId",
    "averagedUnrelated",
    "historyValid",
    "textureRetained",
    "motionRetained",
)
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
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")


def evaluate(payload: dict) -> dict:
    """Keep motion and texture. Reject an average of unrelated frames."""
    event, region, averaged, history, texture, motion = _payload(payload)
    preserved = [
        f"event:{event}",
        f"region:{region}",
        f"texture:{str(texture).lower()}",
        f"motion:{str(motion).lower()}",
        f"history-valid:{str(history).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    if averaged:
        return _result(
            "rejected",
            reasons + [NEGATIVE],
            ["unrelated-frame-average"],
            preserved,
            ["unrelated frames were not averaged"],
        )
    if not texture or not motion:
        claims = []
        if not texture:
            claims.append("texture-lost")
        if not motion:
            claims.append("motion-lost")
        return _result(
            "rejected",
            reasons + ["motion or texture left the quality gate"],
            claims,
            preserved,
            list(claims),
        )
    if not history:
        reasons.append(f"{event} reduced reliance on invalid history")
        return _result(
            "history_reduced",
            reasons,
            [],
            preserved,
            ["invalid history was not reused"],
        )
    reasons.append(f"{event} preserved motion and texture")
    return _result(
        "motion_preserved",
        reasons,
        [],
        preserved,
        ["temporal gate is not a physical noise measurement"],
    )


def _payload(payload: object) -> tuple[str, str, bool, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    event = payload["event"]
    if event not in _EVENTS:
        raise ValueError("event is unknown")
    region = payload["regionId"]
    if not isinstance(region, str) or _TOKEN.fullmatch(region) is None:
        raise ValueError("regionId must be a token")
    flags = (
        payload["averagedUnrelated"],
        payload["historyValid"],
        payload["textureRetained"],
        payload["motionRetained"],
    )
    if any(type(item) is not bool for item in flags):
        raise ValueError("temporal flags must be bools")
    return event, region, flags[0], flags[1], flags[2], flags[3]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("temporal decision cannot be qualified or allowed")
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
