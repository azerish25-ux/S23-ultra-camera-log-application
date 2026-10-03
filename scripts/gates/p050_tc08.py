"""TC-P050-08 independent reference disagreement.

Intervention: Compare the optimized implementation with a separately constructed
small mathematical oracle.
Expected: Explain intentional algorithm differences and fail unintended numeric
or geometric mismatches.
Negative: Copying the implementation into its own test oracle must not count as
independent validation.
"""

from __future__ import annotations


CASE_ID = "TC-P050-08"
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

_PRECISIONS = ("f32", "f64", "int")
_MISMATCHES = ("none", "numeric", "geometric", "intentional")
_ORACLES = ("independent", "copied")
_PAYLOAD_KEYS = ("precision", "size", "seed", "oracleKind", "mismatch", "explanation")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "explained", "agreed")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Fail a copied oracle or an unintended mismatch. Intentional gaps need an explanation."""
    precision, size, seed, kind, mismatch, explanation = _payload(payload)
    preserved = [
        f"precision:{precision}",
        f"size:{size}",
        f"seed:{seed}",
        f"oracle:{kind}",
        f"mismatch:{mismatch}",
    ]
    if kind == "copied":
        reasons = [EXPECTED, NEGATIVE, "copied oracle is not independent validation"]
        return _result(
            "rejected",
            reasons,
            ["copied-oracle"],
            preserved,
            ["independent oracle was not replaced by the implementation"],
        )
    if mismatch in ("numeric", "geometric"):
        reasons = [EXPECTED, f"unintended {mismatch} mismatch failed"]
        return _result(
            "rejected",
            reasons,
            ["unintended-mismatch"],
            preserved,
            ["mismatch was not absorbed into the oracle"],
        )
    if mismatch == "intentional":
        reasons = [EXPECTED, "intentional algorithm difference explained", explanation]
        return _result("explained", reasons, [], preserved, ["explanation is not a qualification"])
    reasons = [EXPECTED, "independent oracle agreed", f"precision:{precision}"]
    return _result("agreed", reasons, [], preserved, [])


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    precision = payload["precision"]
    if precision not in _PRECISIONS:
        raise ValueError("precision must be f32, f64, or int")
    size = payload["size"]
    if type(size) is not int or size < 1 or size > 64:
        raise ValueError("size must be an int from 1 through 64")
    seed = payload["seed"]
    if type(seed) is not int or seed < 0 or seed > 10000:
        raise ValueError("seed must be an int from 0 through 10000")
    kind = payload["oracleKind"]
    if kind not in _ORACLES:
        raise ValueError("oracleKind must be independent or copied")
    mismatch = payload["mismatch"]
    if mismatch not in _MISMATCHES:
        raise ValueError("mismatch must be none, numeric, geometric, or intentional")
    explanation = payload["explanation"]
    if not isinstance(explanation, str) or explanation != explanation.strip():
        raise ValueError("explanation must be a string")
    if mismatch == "intentional" and not explanation:
        raise ValueError("intentional mismatch requires an explanation")
    if mismatch != "intentional" and explanation:
        raise ValueError("explanation is only allowed for an intentional mismatch")
    return precision, size, seed, kind, mismatch, explanation


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
