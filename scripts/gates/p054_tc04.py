"""TC-P054-04 nonlinear processing order.

Intervention: Move a reduction, blur, exposure scale, or color operation
across an encoding boundary deliberately.
Expected: Detect disagreement with the declared domain-specific reference and
reject the altered graph.
Negative: A visually plausible result is insufficient when operation order
violates the contract.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P054-04"
INTERVENTION = (
    "Move a reduction, blur, exposure scale, or color operation across an encoding boundary deliberately."
)
EXPECTED = (
    "Detect disagreement with the declared domain-specific reference and reject the altered graph."
)
NEGATIVE = "A visually plausible result is insufficient when operation order violates the contract."

_OPS = ("reduction", "blur", "exposure-scale", "color")
_DOMAINS = ("scene-linear", "logarithmic", "display-encoded")
_PAYLOAD_KEYS = ("operation", "appliedDomain", "declaredDomain", "referenceDelta", "plausible")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Reject a denoise step that crosses the declared encoding domain."""
    operation, applied, declared, delta, plausible = _payload(payload)
    preserved = [
        operation,
        applied,
        declared,
        f"delta:{delta}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"{operation} applied in {applied} declared {declared}"]
    rejected: list[str] = []
    questions = [f"reference delta {delta}"]
    if applied != declared:
        rejected.append("order-violation")
        reasons.append("operation domain disagrees with the declared domain")
    if Decimal(delta) > 0:
        rejected.append("reference-disagreement")
        reasons.append("numeric result disagrees with the domain-specific reference")
    if plausible and rejected:
        rejected.append("plausible-not-sufficient")
        reasons.append(NEGATIVE)
    if rejected:
        decision = "rejected"
        questions.append("altered graph was rejected; domains stay in the inventory")
    else:
        decision = "domain-matched"
        reasons.append("operation stayed in the declared domain and matched the reference")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    operation = payload["operation"]
    if operation not in _OPS:
        raise ValueError("operation is unsupported")
    applied = payload["appliedDomain"]
    declared = payload["declaredDomain"]
    if applied not in _DOMAINS or declared not in _DOMAINS:
        raise ValueError("domain is unsupported")
    delta = payload["referenceDelta"]
    if not isinstance(delta, str) or _DECIMAL.fullmatch(delta) is None:
        raise ValueError("referenceDelta must be a canonical decimal string")
    plausible = payload["plausible"]
    if type(plausible) is not bool:
        raise ValueError("plausible must be a bool")
    return operation, applied, declared, delta, plausible


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P054-04 must not yield qualified or allowed")
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
