"""TC-P056-04 nonlinear processing order.

Intervention: Move a reduction, blur, exposure scale, or color operation across
an encoding boundary deliberately.
Expected: Detect disagreement with the declared domain-specific reference and
reject the altered graph.
Negative: A visually plausible result is insufficient when operation order
violates the contract.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P056-04"
INTERVENTION = (
    "Move a reduction, blur, exposure scale, or color operation across an encoding boundary "
    "deliberately."
)
EXPECTED = (
    "Detect disagreement with the declared domain-specific reference and reject the altered graph."
)
NEGATIVE = "A visually plausible result is insufficient when operation order violates the contract."

_OPS = ("reduction", "blur", "exposure", "color")
_DOMAINS = ("logarithmic", "display-encoded", "scene-linear")
_ORDERS = ("before-encoding", "after-encoding")
_PAYLOAD_KEYS = (
    "operation",
    "domain",
    "order",
    "matchesReference",
    "visuallyPlausible",
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


def evaluate(payload: dict) -> dict:
    """Reject an operation that crosses into an encoded domain, even if it looks plausible."""
    operation, domain, order, matches, plausible = _payload(payload)
    preserved = [
        f"operation:{operation}",
        f"domain:{domain}",
        f"order:{order}",
        f"plausible:{str(plausible).lower()}",
    ]
    rejected: list[str] = []
    questions: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"{operation} in {domain} {order}"]
    illegal_domain = domain != "scene-linear" or order != "before-encoding"
    if illegal_domain:
        rejected.append("encoded-domain-order")
        reasons.append("reduction and related ops stay scene-linear and before encoding")
    if not matches:
        rejected.append("reference-disagreement")
        reasons.append("the graph disagrees with the declared domain-specific reference")
    if plausible and (illegal_domain or not matches):
        rejected.append("plausible-but-illegal-order")
        reasons.append(NEGATIVE)
        questions.append("visual plausibility did not accept the altered graph")
    if rejected:
        decision = "rejected"
        if not any(item == "visual plausibility did not accept the altered graph" for item in questions):
            questions.append(f"{domain} {operation} was rejected")
    else:
        decision = "order-kept"
        reasons.append("scene-linear order matches the declared reference")
        questions.append(f"{operation} stayed before encoding")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    operation = payload["operation"]
    if operation not in _OPS:
        raise ValueError("operation is unsupported")
    domain = payload["domain"]
    if domain not in _DOMAINS:
        raise ValueError("domain is unsupported")
    order = payload["order"]
    if order not in _ORDERS:
        raise ValueError("order is unsupported")
    matches = payload["matchesReference"]
    plausible = payload["visuallyPlausible"]
    if type(matches) is not bool or type(plausible) is not bool:
        raise ValueError("matchesReference and visuallyPlausible must be bools")
    if _TOKEN.fullmatch(operation) is None:
        raise ValueError("operation must be a token")
    return operation, domain, order, matches, plausible


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P056-04 must not yield qualified or allowed")
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
