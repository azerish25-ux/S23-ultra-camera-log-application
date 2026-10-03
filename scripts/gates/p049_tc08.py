"""TC-P049-08 independent reference disagreement.

Intervention: Compare the optimized implementation with a separately
constructed small mathematical oracle.
Expected: Explain intentional algorithm differences and fail unintended
numeric or geometric mismatches.
Negative: Copying the implementation into its own test oracle must not count
as independent validation.
"""

from __future__ import annotations


CASE_ID = "TC-P049-08"
INTERVENTION = (
    "Compare the optimized implementation with a separately constructed small "
    "mathematical oracle."
)
EXPECTED = (
    "Explain intentional algorithm differences and fail unintended numeric or geometric "
    "mismatches."
)
NEGATIVE = (
    "Copying the implementation into its own test oracle must not count as independent "
    "validation."
)

_PRECISIONS = ("integer", "rational", "high")
_SIZES = ("tiny", "small", "medium")
_KINDS = ("independent", "copied-implementation")
_MISMATCH = ("none", "numeric", "geometric", "intentional")
_PAYLOAD_KEYS = ("precision", "sourceSize", "seed", "oracleKind", "mismatch")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld", "compared")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Fail copied oracles and unintended mismatches. Explain intentional ones."""
    precision, size, seed, kind, mismatch = _payload(payload)
    preserved = [
        f"precision:{precision}",
        f"source-size:{size}",
        f"seed:{seed}",
        f"oracle:{kind}",
    ]
    reasons = [EXPECTED]
    if kind == "copied-implementation":
        decision = "rejected"
        rejected = ["copied-implementation-oracle"]
        reasons.append(NEGATIVE)
        questions = ["a copied implementation is not an independent oracle"]
    elif mismatch == "numeric":
        decision = "rejected"
        rejected = ["numeric-mismatch"]
        reasons.append("unintended numeric mismatch failed")
        questions = ["numeric disagreement was not explained away"]
    elif mismatch == "geometric":
        decision = "rejected"
        rejected = ["geometric-mismatch"]
        reasons.append("unintended geometric mismatch failed")
        questions = ["geometric disagreement was not explained away"]
    elif mismatch == "intentional":
        decision = "withheld"
        rejected = []
        reasons.append("intentional algorithm difference recorded")
        questions = ["intentional difference is not independent agreement"]
    else:
        decision = "compared"
        rejected = []
        reasons.append("independent oracle agrees at this precision, size, and seed")
        questions = ["agreement is not physical S23 qualification"]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    precision = payload["precision"]
    size = payload["sourceSize"]
    kind = payload["oracleKind"]
    mismatch = payload["mismatch"]
    if precision not in _PRECISIONS:
        raise ValueError("precision is unknown")
    if size not in _SIZES:
        raise ValueError("sourceSize is unknown")
    if kind not in _KINDS:
        raise ValueError("oracleKind is unknown")
    if mismatch not in _MISMATCH:
        raise ValueError("mismatch is unknown")
    seed = payload["seed"]
    if not isinstance(seed, str) or not seed.isdigit() or (seed != "0" and seed[0] == "0"):
        raise ValueError("seed must be a canonical non-negative integer string")
    return precision, size, seed, kind, mismatch


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("decision cannot be qualified or allowed")
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
