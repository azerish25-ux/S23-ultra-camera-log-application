"""TC-P055-08 independent reference disagreement.

Intervention: Compare the optimized implementation with a separately
constructed small mathematical oracle.
Expected: Explain intentional algorithm differences and fail unintended
numeric or geometric mismatches.
Negative: Copying the implementation into its own test oracle must not count
as independent validation.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P055-08"
INTERVENTION = (
    "Compare the optimized implementation with a separately constructed small mathematical oracle."
)
EXPECTED = (
    "Explain intentional algorithm differences and fail unintended numeric or geometric mismatches."
)
NEGATIVE = (
    "Copying the implementation into its own test oracle must not count as independent validation."
)
REPEAT = "Repeat at multiple precisions, source sizes, and deterministic seeds."

_PRECISIONS = ("float16", "float32", "float64")
_MISMATCHES = ("none", "numeric", "geometric")
_PAYLOAD_KEYS = (
    "precision",
    "sourceSize",
    "seed",
    "copiedOracle",
    "mismatch",
    "intentionalNote",
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


def evaluate(payload: dict) -> dict:
    """Fail a copied oracle or an unexplained numeric or geometric mismatch."""
    precision, size, seed, copied, mismatch, note = _payload(payload)
    preserved = [
        f"precision:{precision}",
        f"size:{size}",
        f"seed:{seed}",
        f"mismatch:{mismatch}",
        f"copied:{str(copied).lower()}",
    ]
    if note:
        preserved.append(f"note:{note}")
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}"]
    if copied:
        decision = "rejected"
        rejected = ["copied-oracle"]
        reasons.append(NEGATIVE)
        questions.append("a copied implementation oracle was not treated as independent")
    elif mismatch != "none" and not note:
        decision = "rejected"
        rejected = [f"unintended-{mismatch}"]
        reasons.append(f"unintended {mismatch} mismatch failed")
    elif mismatch != "none":
        decision = "explained"
        rejected = []
        reasons.append(f"intentional {mismatch} difference: {note}")
    else:
        decision = "compared"
        rejected = []
        reasons.append("independent oracle agreed at this precision, size, and seed")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    precision = payload["precision"]
    if precision not in _PRECISIONS:
        raise ValueError("precision is unsupported")
    size = payload["sourceSize"]
    seed = payload["seed"]
    if not isinstance(size, str) or _TOKEN.fullmatch(size) is None:
        raise ValueError("sourceSize must be a token")
    if not isinstance(seed, str) or _TOKEN.fullmatch(seed) is None:
        raise ValueError("seed must be a token")
    copied = payload["copiedOracle"]
    if type(copied) is not bool:
        raise ValueError("copiedOracle must be a bool")
    mismatch = payload["mismatch"]
    if mismatch not in _MISMATCHES:
        raise ValueError("mismatch is unsupported")
    note = payload["intentionalNote"]
    if not isinstance(note, str):
        raise ValueError("intentionalNote must be a string")
    if note and _TOKEN.fullmatch(note) is None:
        raise ValueError("intentionalNote must be empty or a token")
    return precision, size, seed, copied, mismatch, note


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P055-08 must not yield qualified or allowed")
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
