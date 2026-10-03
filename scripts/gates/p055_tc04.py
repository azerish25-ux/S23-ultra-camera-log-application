"""TC-P055-04 nonlinear processing order.

Intervention: Move a reduction, blur, exposure scale, or color operation
across an encoding boundary deliberately.
Expected: Detect disagreement with the declared domain-specific reference and
reject the altered graph.
Negative: A visually plausible result is insufficient when operation order
violates the contract.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P055-04"
INTERVENTION = (
    "Move a reduction, blur, exposure scale, or color operation across an encoding "
    "boundary deliberately."
)
EXPECTED = (
    "Detect disagreement with the declared domain-specific reference and reject the altered graph."
)
NEGATIVE = "A visually plausible result is insufficient when operation order violates the contract."
REPEAT = "Repeat with logarithmic, display-encoded, and scene-linear fixtures."

_OPS = ("reduction", "blur", "exposure-scale", "color")
_DOMAINS = ("logarithmic", "display-encoded", "scene-linear")
_PAYLOAD_KEYS = (
    "graphId",
    "operation",
    "domain",
    "movedAcrossBoundary",
    "referenceAgrees",
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
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")


def evaluate(payload: dict) -> dict:
    """Reject an altered graph that disagrees with the domain reference."""
    graph, operation, domain, moved, agrees, plausible = _payload(payload)
    preserved = [
        f"graph:{graph}",
        f"operation:{operation}",
        f"domain:{domain}",
        f"moved:{str(moved).lower()}",
        f"reference-agrees:{str(agrees).lower()}",
        f"plausible:{str(plausible).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [f"repeat coverage includes {REPEAT}"]
    if moved and not agrees:
        decision = "rejected"
        rejected.append("altered-graph")
        reasons.append(f"{operation} moved across the {domain} boundary and disagrees")
        if plausible:
            rejected.append("visually-plausible-insufficient")
            reasons.append(NEGATIVE)
    elif not agrees:
        decision = "rejected"
        rejected.append("reference-disagreement")
        reasons.append(f"{domain} reference disagrees")
    elif moved:
        decision = "withheld"
        questions.append("the move did not disagree on this host fixture")
        reasons.append("no disagreement was detected, so the graph was not accepted")
    else:
        decision = "order_held"
        reasons.append(f"{operation} stayed in the declared {domain} domain")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    graph = payload["graphId"]
    if not isinstance(graph, str) or _TOKEN.fullmatch(graph) is None:
        raise ValueError("graphId must be a token")
    operation = payload["operation"]
    if operation not in _OPS:
        raise ValueError("operation is unsupported")
    domain = payload["domain"]
    if domain not in _DOMAINS:
        raise ValueError("domain is unsupported")
    moved = payload["movedAcrossBoundary"]
    agrees = payload["referenceAgrees"]
    plausible = payload["visuallyPlausible"]
    if type(moved) is not bool or type(agrees) is not bool or type(plausible) is not bool:
        raise ValueError("flags must be bools")
    return graph, operation, domain, moved, agrees, plausible


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P055-04 must not yield qualified or allowed")
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
