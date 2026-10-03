"""TC-P054-08 independent reference disagreement.

Intervention: Compare the optimized implementation with a separately
constructed small mathematical oracle.
Expected: Explain intentional algorithm differences and fail unintended
numeric or geometric mismatches.
Negative: Copying the implementation into its own test oracle must not count
as independent validation.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P054-08"
INTERVENTION = (
    "Compare the optimized implementation with a separately constructed small mathematical oracle."
)
EXPECTED = (
    "Explain intentional algorithm differences and fail unintended numeric or geometric mismatches."
)
NEGATIVE = "Copying the implementation into its own test oracle must not count as independent validation."

_PRECISIONS = ("fp32", "fp64", "decimal")
_ORACLES = ("independent", "copied-implementation")
_PAYLOAD_KEYS = (
    "precision",
    "sourceSize",
    "seed",
    "oracleKind",
    "numericDelta",
    "geometricDelta",
    "intentional",
    "explanation",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")
_UINT = re.compile(r"0|[1-9][0-9]*")
_SIZE = re.compile(r"[1-9][0-9]*x[1-9][0-9]*")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Require an independent oracle. A copied implementation is not validation."""
    precision, size, seed, kind, numeric, geometric, intentional, explanation = _payload(payload)
    preserved = [
        precision,
        size,
        f"seed:{seed}",
        f"numeric:{numeric}",
        f"geometric:{geometric}",
        kind,
    ]
    reasons = [EXPECTED, INTERVENTION, f"{precision} {size} seed {seed}"]
    rejected: list[str] = []
    questions = [f"oracle {kind}"]
    if kind == "copied-implementation":
        rejected.append("copied-oracle")
        reasons.append(NEGATIVE)
        questions.append("copied implementation was not treated as an independent oracle")
    if Decimal(numeric) > 0:
        rejected.append("numeric-mismatch")
        reasons.append(f"numeric delta {numeric}")
    if Decimal(geometric) > 0:
        rejected.append("geometric-mismatch")
        reasons.append(f"geometric delta {geometric}")
    if intentional and not rejected:
        decision = "explained-difference"
        reasons.append(f"intentional difference explained as {explanation}")
        questions.append(explanation)
    elif rejected:
        decision = "rejected"
        if intentional:
            reasons.append(f"explanation {explanation} does not excuse the mismatch class")
        questions.append("mismatch or copied oracle stayed rejected")
    else:
        decision = "oracle-agreed"
        reasons.append("independent oracle matched at this precision, size, and seed")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, str, str, str, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    precision = payload["precision"]
    if precision not in _PRECISIONS:
        raise ValueError("precision is unsupported")
    size = payload["sourceSize"]
    if not isinstance(size, str) or _SIZE.fullmatch(size) is None:
        raise ValueError("sourceSize must look like 8x8")
    seed = payload["seed"]
    if not isinstance(seed, str) or _UINT.fullmatch(seed) is None:
        raise ValueError("seed must be a canonical non-negative integer string")
    kind = payload["oracleKind"]
    if kind not in _ORACLES:
        raise ValueError("oracleKind is unsupported")
    numeric = _decimal(payload["numericDelta"], "numericDelta")
    geometric = _decimal(payload["geometricDelta"], "geometricDelta")
    intentional = payload["intentional"]
    if type(intentional) is not bool:
        raise ValueError("intentional must be a bool")
    explanation = payload["explanation"]
    if not isinstance(explanation, str) or _TOKEN.fullmatch(explanation) is None:
        raise ValueError("explanation must be a token")
    if intentional and explanation == "none":
        raise ValueError("intentional differences require an explanation")
    if not intentional and explanation != "none":
        raise ValueError("explanation requires intentional")
    return precision, size, seed, kind, numeric, geometric, intentional, explanation


def _decimal(value: object, label: str) -> str:
    if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
        raise ValueError(f"{label} must be a canonical decimal string")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P054-08 must not yield qualified or allowed")
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
