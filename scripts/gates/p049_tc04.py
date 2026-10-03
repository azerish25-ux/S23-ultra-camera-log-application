"""TC-P049-04 nonlinear processing order.

Intervention: Move a reduction, blur, exposure scale, or color operation
across an encoding boundary deliberately.
Expected: Detect disagreement with the declared domain-specific reference and
reject the altered graph.
Negative: A visually plausible result is insufficient when operation order
violates the contract.
"""

from __future__ import annotations


CASE_ID = "TC-P049-04"
INTERVENTION = (
    "Move a reduction, blur, exposure scale, or color operation across an encoding "
    "boundary deliberately."
)
EXPECTED = (
    "Detect disagreement with the declared domain-specific reference and reject the "
    "altered graph."
)
NEGATIVE = (
    "A visually plausible result is insufficient when operation order violates the contract."
)

_DOMAINS = ("logarithmic", "display-encoded", "scene-linear")
_OPS = ("reduction", "blur", "exposure-scale", "color")
_PAYLOAD_KEYS = ("domain", "operation", "movedAcrossEncoding", "plausible")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "order_held")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Reject an operation moved across the encoding boundary, even if plausible."""
    domain, operation, moved, plausible = _payload(payload)
    preserved = [
        f"domain:{domain}",
        f"operation:{operation}",
        f"plausible:{str(plausible).lower()}",
    ]
    reasons = [EXPECTED]
    if moved:
        decision = "rejected"
        rejected = ["order-violation", f"{operation}-across-{domain}"]
        reasons.append(NEGATIVE)
        if plausible:
            reasons.append("visually plausible result does not excuse the order violation")
        questions = [f"{domain} reference disagrees with the altered graph"]
    else:
        decision = "order_held"
        rejected = []
        reasons.append("declared domain-specific reference agrees")
        questions = ["operation stayed in the declared domain"]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    domain = payload["domain"]
    operation = payload["operation"]
    if domain not in _DOMAINS:
        raise ValueError("domain is unknown")
    if operation not in _OPS:
        raise ValueError("operation is unknown")
    moved = payload["movedAcrossEncoding"]
    plausible = payload["plausible"]
    if type(moved) is not bool or type(plausible) is not bool:
        raise ValueError("movedAcrossEncoding and plausible must be bools")
    return domain, operation, moved, plausible


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
