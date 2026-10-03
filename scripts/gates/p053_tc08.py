"""TC-P053-08 independent reference disagreement.

Intervention: Compare the optimized implementation with a separately constructed
small mathematical oracle.
Expected: Explain intentional algorithm differences and fail unintended numeric
or geometric mismatches.
Negative: Copying the implementation into its own test oracle must not count as
independent validation.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P053-08"
INTERVENTION = (
    "Compare the optimized implementation with a separately constructed small mathematical oracle."
)
EXPECTED = (
    "Explain intentional algorithm differences and fail unintended numeric or geometric mismatches."
)
NEGATIVE = (
    "Copying the implementation into its own test oracle must not count as independent validation."
)

_PRECISIONS = ("half", "single", "double", "rational")
_PAYLOAD_KEYS = (
    "precision",
    "sourceSize",
    "seed",
    "independentOracle",
    "copiedImplementation",
    "intentionalDifference",
    "numericMismatch",
    "geometricMismatch",
    "differenceNote",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "explained", "independent_check")
_FORBIDDEN = {"qualified", "allowed"}
_TOKEN = re.compile(r"^[A-Za-z0-9._:-]+$")


def evaluate(payload: dict) -> dict:
    """Require a separate oracle. A copied implementation is not validation."""
    (
        precision,
        source_size,
        seed,
        independent,
        copied,
        intentional,
        numeric,
        geometric,
        note,
    ) = _payload(payload)
    preserved = [
        f"precision:{precision}",
        f"source-size:{source_size}",
        f"seed:{seed}",
        f"note:{note}" if note else "note:none",
    ]
    reasons = [EXPECTED, INTERVENTION]
    if copied or not independent:
        return _result(
            "rejected",
            reasons + [NEGATIVE],
            ["self-oracle"],
            preserved,
            ["the implementation cannot validate itself"],
        )
    mismatch = numeric or geometric
    if mismatch and not intentional:
        claims = []
        if numeric:
            claims.append("numeric-mismatch")
        if geometric:
            claims.append("geometric-mismatch")
        return _result(
            "rejected",
            reasons + ["unintended mismatch failed"],
            claims,
            preserved,
            list(claims),
        )
    if mismatch and intentional:
        reasons.append("intentional difference explained: " + note)
        return _result(
            "explained",
            reasons,
            [],
            preserved,
            ["explained difference is not a qualification"],
        )
    reasons.append(f"independent oracle agrees at {precision} size {source_size}")
    return _result(
        "independent_check",
        reasons,
        [],
        preserved,
        ["agreement is not physical S23 qualification"],
    )


def _payload(payload: object) -> tuple[str, int, str, bool, bool, bool, bool, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    precision = payload["precision"]
    if precision not in _PRECISIONS:
        raise ValueError("precision is unknown")
    source_size = payload["sourceSize"]
    if type(source_size) is not int or source_size <= 0:
        raise ValueError("sourceSize must be a positive int")
    seed = payload["seed"]
    if not isinstance(seed, str) or _TOKEN.fullmatch(seed) is None:
        raise ValueError("seed must be a token")
    flags = (
        payload["independentOracle"],
        payload["copiedImplementation"],
        payload["intentionalDifference"],
        payload["numericMismatch"],
        payload["geometricMismatch"],
    )
    if any(type(item) is not bool for item in flags):
        raise ValueError("oracle flags must be bools")
    note = payload["differenceNote"]
    if not isinstance(note, str) or len(note) > 120 or any(ord(char) < 32 for char in note):
        raise ValueError("differenceNote must be a short string")
    intentional = flags[2]
    if intentional and not note.strip():
        raise ValueError("an intentional difference needs a note")
    if not intentional and note != "":
        raise ValueError("differenceNote must be empty unless the difference is intentional")
    return (
        precision,
        source_size,
        seed,
        flags[0],
        flags[1],
        intentional,
        flags[3],
        flags[4],
        note,
    )


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("oracle decision cannot be qualified or allowed")
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
