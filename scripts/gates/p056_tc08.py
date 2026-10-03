"""TC-P056-08 independent reference disagreement.

Intervention: Compare the optimized implementation with a separately constructed
small mathematical oracle.
Expected: Explain intentional algorithm differences and fail unintended numeric
or geometric mismatches.
Negative: Copying the implementation into its own test oracle must not count as
independent validation.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P056-08"
INTERVENTION = (
    "Compare the optimized implementation with a separately constructed small mathematical oracle."
)
EXPECTED = (
    "Explain intentional algorithm differences and fail unintended numeric or geometric mismatches."
)
NEGATIVE = "Copying the implementation into its own test oracle must not count as independent validation."

_PRECISIONS = ("binary32", "decimal", "integer")
_PAYLOAD_KEYS = (
    "precision",
    "sourceSize",
    "seed",
    "oracleCopied",
    "numericMismatch",
    "geometricMismatch",
    "intentionalDifference",
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
_SIZE = re.compile(r"[1-9][0-9]*x[1-9][0-9]*")
_SEED = re.compile(r"[A-Za-z0-9._-]{1,32}")


def evaluate(payload: dict) -> dict:
    """Fail a copied oracle and any unintended numeric or geometric mismatch."""
    precision, size, seed, copied, numeric, geometric, intentional, note = _payload(payload)
    preserved = [
        f"precision:{precision}",
        f"size:{size}",
        f"seed:{seed}",
        f"numeric:{str(numeric).lower()}",
        f"geometric:{str(geometric).lower()}",
    ]
    rejected: list[str] = []
    questions: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"oracle {precision} {size} seed {seed}"]
    if copied:
        rejected.append("copied-oracle")
        reasons.append(NEGATIVE)
        questions.append("a copied implementation is not an independent oracle")
    if numeric and not (intentional and not copied):
        rejected.append("numeric-mismatch")
    if geometric and not (intentional and not copied):
        rejected.append("geometric-mismatch")
    if copied:
        decision = "rejected"
        if numeric:
            reasons.append("numeric mismatch stayed visible beside the copied oracle")
        if geometric:
            reasons.append("geometric mismatch stayed visible beside the copied oracle")
    elif (numeric or geometric) and not intentional:
        decision = "rejected"
        reasons.append("unintended mismatch failed the independent oracle")
        questions.append(f"{precision} comparison rejected")
    elif numeric or geometric:
        decision = "explained"
        reasons.append(note)
        reasons.append("intentional algorithm difference is not a pass and not qualification")
        questions.append(note)
    else:
        decision = "withheld"
        reasons.append("agreement with the small oracle is not qualification")
        questions.append("no mismatch was observed; the host fixture is still not qualified")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, bool, bool, bool, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    precision = payload["precision"]
    if precision not in _PRECISIONS:
        raise ValueError("precision is unsupported")
    size = payload["sourceSize"]
    if not isinstance(size, str) or _SIZE.fullmatch(size) is None:
        raise ValueError("sourceSize must look like 4x4")
    seed = payload["seed"]
    if not isinstance(seed, str) or _SEED.fullmatch(seed) is None:
        raise ValueError("seed must be a token")
    flags = []
    for name in ("oracleCopied", "numericMismatch", "geometricMismatch", "intentionalDifference"):
        value = payload[name]
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(value)
    note = payload["differenceNote"]
    if not isinstance(note, str):
        raise ValueError("differenceNote must be a string")
    copied, numeric, geometric, intentional = flags
    if intentional and not note.strip():
        raise ValueError("intentionalDifference requires a differenceNote")
    if intentional and not (numeric or geometric):
        raise ValueError("intentionalDifference requires a mismatch")
    if note and not intentional:
        raise ValueError("differenceNote requires intentionalDifference")
    return precision, size, seed, copied, numeric, geometric, intentional, note


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P056-08 must not yield qualified or allowed")
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
