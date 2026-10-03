"""TC-P052-04 nonlinear processing order.

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


CASE_ID = "TC-P052-04"
INTERVENTION = (
    "Move a reduction, blur, exposure scale, or color operation across an encoding boundary deliberately."
)
EXPECTED = (
    "Detect disagreement with the declared domain-specific reference and reject the altered graph."
)
NEGATIVE = "A visually plausible result is insufficient when operation order violates the contract."

_DOMAINS = ("logarithmic", "display-encoded", "scene-linear")
_OPERATIONS = ("reduction", "blur", "exposure-scale", "color")
_ORDERS = ("before-encode", "after-encode")
_PAYLOAD_KEYS = (
    "domain",
    "operation",
    "declaredOrder",
    "appliedOrder",
    "visuallyPlausible",
    "disagreement",
)
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
    """Reject a graph that crosses the encoding boundary out of order."""
    domain, operation, declared, applied, plausible, disagreement = _payload(payload)
    preserved = [
        f"domain:{domain}",
        f"operation:{operation}",
        f"declared:{declared}",
        f"applied:{applied}",
        f"disagreement:{disagreement}",
        f"plausible:{str(plausible).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [f"{domain} reference stays attached to the graph"]
    if applied != declared:
        decision = "rejected"
        rejected.append("order-violation")
        if plausible:
            rejected.append("plausible-insufficient")
        reasons.append(NEGATIVE if plausible else "operation order disagrees with the declared graph")
        questions.append("altered graph rejected")
    elif Decimal(disagreement) > 0:
        decision = "rejected"
        rejected.append("domain-disagreement")
        reasons.append(f"{domain} reference disagreement is {disagreement}")
        questions.append("domain reference was not replaced by a visual check")
    else:
        decision = "ordered"
        reasons.append(f"{operation} stays {declared} in {domain}")
        questions.append("ordered is not a physical processing qualification")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, str, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    domain = payload["domain"]
    if domain not in _DOMAINS:
        raise ValueError("domain is unsupported")
    operation = payload["operation"]
    if operation not in _OPERATIONS:
        raise ValueError("operation is unsupported")
    declared = payload["declaredOrder"]
    applied = payload["appliedOrder"]
    if declared not in _ORDERS or applied not in _ORDERS:
        raise ValueError("order must be before-encode or after-encode")
    plausible = payload["visuallyPlausible"]
    if type(plausible) is not bool:
        raise ValueError("visuallyPlausible must be a bool")
    disagreement = payload["disagreement"]
    if not isinstance(disagreement, str) or _DECIMAL.fullmatch(disagreement) is None:
        raise ValueError("disagreement must be a canonical decimal")
    return domain, operation, declared, applied, plausible, disagreement


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P052-04 must not yield qualified or allowed")
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
