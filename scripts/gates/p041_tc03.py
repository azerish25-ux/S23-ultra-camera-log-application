"""TC-P041-03 matrix convention mismatch.

A transposed, reversed, or mis-directed transform fails the neutral and
color-vector checks. A finite determinant does not certify the transform.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P041-03"
INTERVENTION = (
    "Transpose or reverse one calibration transform while keeping all numbers finite and plausible."
)
EXPECTED = "Fail the independent neutral and color-vector checks with a specific convention error."
NEGATIVE = "A finite determinant alone must not certify a color transform."

_FAULTS = (
    "none",
    "transposed",
    "reversed",
    "wrong-white-point",
    "duplicated-white-balance",
    "swapped-direction",
)
_VECTOR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9,._-]{0,79}$")
_PAYLOAD_KEYS = (
    "fault",
    "determinantFinite",
    "neutralVector",
    "colorVector",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "convention_checked"}
_FORBIDDEN = {"qualified", "allowed", "certified"}


def evaluate(payload: dict) -> dict:
    """Fail convention checks. Do not certify from a finite determinant."""
    fault, finite, neutral, color = _payload(payload)
    preserved = [
        f"neutral:{neutral}",
        f"color:{color}",
        f"fault:{fault}",
        f"determinantFinite:{str(finite).lower()}",
    ]
    claims: list[str] = []
    reasons = [EXPECTED]
    if not finite:
        claims.append("non-finite-determinant")
        reasons.append("determinant is not finite")
    if fault != "none":
        claims.extend([fault, "neutral-check-failed", "color-vector-check-failed"])
        reasons.append(f"convention error {fault}")
        reasons.append("independent neutral check failed")
        reasons.append("independent color-vector check failed")
    if finite:
        reasons.append(NEGATIVE)
        reasons.append("finite determinant was not treated as certification")
    if claims:
        return _result(
            "rejected",
            reasons,
            claims,
            preserved,
            ["convention mismatch is not a certified transform"],
        )
    return _result(
        "convention_checked",
        reasons + ["neutral and color-vector checks passed for the declared convention"],
        [],
        preserved,
        ["not a certified color transform"],
    )


def _payload(payload: object) -> tuple[str, bool, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    fault = payload["fault"]
    if fault not in _FAULTS:
        raise ValueError("fault is not a known convention error")
    finite = payload["determinantFinite"]
    if type(finite) is not bool:
        raise ValueError("determinantFinite must be a bool")
    neutral = payload["neutralVector"]
    color = payload["colorVector"]
    if not isinstance(neutral, str) or _VECTOR.fullmatch(neutral) is None:
        raise ValueError("neutralVector must be a short vector token")
    if not isinstance(color, str) or _VECTOR.fullmatch(color) is None:
        raise ValueError("colorVector must be a short vector token")
    return fault, finite, neutral, color


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P041-03 must not yield qualified, allowed, or certified")
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
