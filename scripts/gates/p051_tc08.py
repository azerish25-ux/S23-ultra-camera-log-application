"""TC-P051-08 independent reference disagreement.

Intervention: Compare the optimized implementation with a separately constructed
small mathematical oracle.
Expected: Explain intentional algorithm differences and fail unintended numeric
or geometric mismatches.
Negative: Copying the implementation into its own test oracle must not count as
independent validation.
"""

from __future__ import annotations

CASE_ID = "TC-P051-08"
INTERVENTION = (
    "Compare the optimized implementation with a separately constructed small mathematical oracle."
)
EXPECTED = (
    "Explain intentional algorithm differences and fail unintended numeric or geometric mismatches."
)
NEGATIVE = "Copying the implementation into its own test oracle must not count as independent validation."

_PRECISIONS = ("float32", "float64", "rational")
_SIZES = ("2x2", "4x4", "6x6")
_ORACLES = ("independent", "copied")
_MISMATCHES = ("none", "numeric", "geometric")
_PAYLOAD_KEYS = (
    "precision",
    "sourceSize",
    "seed",
    "oracleKind",
    "mismatch",
    "intentional",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "oracle_agreed", "difference_explained")
_FORBIDDEN = {"qualified", "allowed"}


def independent_total(size: str, seed: int) -> int:
    """Closed form of sum(seed + i) for i in 0..n*n-1. Not a replay of the loop."""
    n = int(size[0])
    count = n * n
    return count * seed + (count - 1) * count // 2


def evaluate(payload: dict) -> dict:
    """Fail a copied oracle and any unintended numeric or geometric mismatch."""
    precision, size, seed, kind, mismatch, intentional = _payload(payload)
    oracle = independent_total(size, seed)
    implementation = oracle if mismatch != "numeric" else oracle + 1
    origin = "1" if mismatch == "geometric" else "0"
    preserved = [
        f"precision:{precision}",
        f"size:{size}",
        f"seed:{seed}",
        f"independent:{oracle}",
        f"implementation:{implementation}",
        f"origin:{origin}",
    ]
    if kind == "copied":
        return _result(
            "rejected",
            [EXPECTED, NEGATIVE, "the oracle was not a copy of the implementation"],
            ["copied-oracle"],
            preserved,
            ["a copied oracle is not independent validation"],
        )
    if mismatch != "none" and not intentional:
        claim = "numeric-mismatch" if mismatch == "numeric" else "geometric-mismatch"
        return _result(
            "rejected",
            [EXPECTED, f"unintended {mismatch} mismatch"],
            [claim],
            preserved,
            [],
        )
    if intentional:
        return _result(
            "difference_explained",
            [EXPECTED, intentional, "intentional difference is not a qualification"],
            [],
            preserved,
            ["explained difference is not physical S23 agreement"],
        )
    return _result(
        "oracle_agreed",
        [EXPECTED, "independent closed form matched", f"total {oracle}"],
        [],
        preserved,
        [],
    )


def _payload(payload: object) -> tuple[str, str, int, str, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    precision = payload["precision"]
    if precision not in _PRECISIONS:
        raise ValueError("precision must be float32, float64, or rational")
    size = payload["sourceSize"]
    if size not in _SIZES:
        raise ValueError("sourceSize must be 2x2, 4x4, or 6x6")
    seed = payload["seed"]
    if type(seed) is not int or not 0 <= seed <= 10000:
        raise ValueError("seed must be an int from 0 through 10000")
    kind = payload["oracleKind"]
    if kind not in _ORACLES:
        raise ValueError("oracleKind must be independent or copied")
    mismatch = payload["mismatch"]
    if mismatch not in _MISMATCHES:
        raise ValueError("mismatch must be none, numeric, or geometric")
    intentional = payload["intentional"]
    if not isinstance(intentional, str) or intentional != intentional.strip():
        raise ValueError("intentional must be a stripped string")
    if mismatch == "none" and intentional:
        raise ValueError("an explanation requires a declared mismatch")
    if kind == "copied" and intentional:
        raise ValueError("a copied oracle cannot be excused as intentional")
    return precision, size, seed, kind, mismatch, intentional


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("oracle decision cannot be qualified or allowed")
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
