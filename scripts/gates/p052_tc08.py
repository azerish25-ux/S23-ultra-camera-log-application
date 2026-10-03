"""TC-P052-08 independent reference disagreement.

Intervention: Compare the optimized implementation with a separately
constructed small mathematical oracle.
Expected: Explain intentional algorithm differences and fail unintended
numeric or geometric mismatches.
Negative: Copying the implementation into its own test oracle must not count
as independent validation.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P052-08"
INTERVENTION = (
    "Compare the optimized implementation with a separately constructed small mathematical oracle."
)
EXPECTED = (
    "Explain intentional algorithm differences and fail unintended numeric or geometric mismatches."
)
NEGATIVE = "Copying the implementation into its own test oracle must not count as independent validation."

_PRECISIONS = ("f32", "f64", "decimal")
_PAYLOAD_KEYS = (
    "precision",
    "sourceSize",
    "seed",
    "independentOracle",
    "intentional",
    "explained",
    "numericMismatch",
    "geometricMismatch",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")


def evaluate(payload: dict) -> dict:
    """Require an independent oracle. A copied implementation is not one."""
    precision, size, seed, independent, intentional, explained, numeric, geometric = _payload(payload)
    preserved = [
        f"precision:{precision}",
        f"size:{size}",
        f"seed:{seed}",
        f"independent:{str(independent).lower()}",
        f"numeric-mismatch:{str(numeric).lower()}",
        f"geometric-mismatch:{str(geometric).lower()}",
        f"intentional:{str(intentional).lower()}",
        f"explained:{str(explained).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [f"{precision} size {size} seed {seed} stays in the inventory"]
    mismatch = numeric or geometric
    if not independent:
        decision = "rejected"
        rejected.append("copied-oracle")
        reasons.append(NEGATIVE)
        questions.append("copied oracle rejected")
    elif mismatch and not intentional:
        decision = "rejected"
        if numeric:
            rejected.append("unintended-numeric")
        if geometric:
            rejected.append("unintended-geometric")
        reasons.append("unintended mismatch failed")
    elif mismatch and intentional and not explained:
        decision = "rejected"
        rejected.append("unexplained-difference")
        reasons.append("intentional difference was not explained")
    elif mismatch and intentional and explained:
        decision = "explained"
        reasons.append("intentional difference explained against an independent oracle")
        questions.append("explained is not physical agreement")
    else:
        decision = "matched"
        reasons.append("independent oracle matched at this precision")
        questions.append("matched is not a physical S23 qualification")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, int, str, bool, bool, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    precision = payload["precision"]
    if precision not in _PRECISIONS:
        raise ValueError("precision is unsupported")
    size = payload["sourceSize"]
    if type(size) is not int or size <= 0:
        raise ValueError("sourceSize must be a positive int")
    seed = payload["seed"]
    if not isinstance(seed, str) or _TOKEN.fullmatch(seed) is None:
        raise ValueError("seed must be a token")
    flags = []
    for name in ("independentOracle", "intentional", "explained", "numericMismatch", "geometricMismatch"):
        value = payload[name]
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(value)
    return (precision, size, seed, *flags)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P052-08 must not yield qualified or allowed")
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
