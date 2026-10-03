"""TC-P053-04 nonlinear processing order.

Intervention: Move a reduction, blur, exposure scale, or color operation across
an encoding boundary deliberately.
Expected: Detect disagreement with the declared domain-specific reference and
reject the altered graph.
Negative: A visually plausible result is insufficient when operation order
violates the contract.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P053-04"
INTERVENTION = (
    "Move a reduction, blur, exposure scale, or color operation across an encoding "
    "boundary deliberately."
)
EXPECTED = (
    "Detect disagreement with the declared domain-specific reference and reject the altered graph."
)
NEGATIVE = (
    "A visually plausible result is insufficient when operation order violates the contract."
)

_OPS = ("reduction", "blur", "exposure-scale", "color")
_DOMAINS = ("logarithmic", "display-encoded", "scene-linear")
_PAYLOAD_KEYS = (
    "operation",
    "domain",
    "declaredOrder",
    "appliedOrder",
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
_DECISIONS = ("rejected", "domain_reference")
_FORBIDDEN = {"qualified", "allowed"}
_TOKEN = re.compile(r"^[a-z0-9-]+$")


def evaluate(payload: dict) -> dict:
    """Reject an operation that crosses the declared encoding boundary."""
    operation, domain, declared, applied, agrees, plausible = _payload(payload)
    preserved = [
        f"operation:{operation}",
        f"domain:{domain}",
        f"declared:{declared}",
        f"applied:{applied}",
        f"plausible:{str(plausible).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    if applied != declared or not agrees:
        rejected = ["order-violation"]
        if not agrees:
            rejected.append("reference-disagreement")
        if plausible:
            rejected.append("visually-plausible-insufficient")
            reasons.append(NEGATIVE)
        else:
            reasons.append("altered graph disagrees with the domain-specific reference")
        return _result("rejected", reasons, rejected, preserved, ["operation order was rejected"])
    reasons.append(f"{operation} stayed in {domain} order {declared}")
    return _result(
        "domain_reference",
        reasons,
        [],
        preserved,
        ["domain agreement is not a physical image grade"],
    )


def _payload(payload: object) -> tuple[str, str, str, str, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    operation = payload["operation"]
    if operation not in _OPS:
        raise ValueError("operation is unknown")
    domain = payload["domain"]
    if domain not in _DOMAINS:
        raise ValueError("domain is unknown")
    declared = payload["declaredOrder"]
    applied = payload["appliedOrder"]
    if not isinstance(declared, str) or _TOKEN.fullmatch(declared) is None:
        raise ValueError("declaredOrder must be a lowercase token")
    if not isinstance(applied, str) or _TOKEN.fullmatch(applied) is None:
        raise ValueError("appliedOrder must be a lowercase token")
    agrees = payload["referenceAgrees"]
    plausible = payload["visuallyPlausible"]
    if type(agrees) is not bool or type(plausible) is not bool:
        raise ValueError("referenceAgrees and visuallyPlausible must be bools")
    return operation, domain, declared, applied, agrees, plausible


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("order decision cannot be qualified or allowed")
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
