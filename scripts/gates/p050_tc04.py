"""TC-P050-04 nonlinear processing order.

Intervention: Move a reduction, blur, exposure scale, or color operation across
an encoding boundary deliberately.
Expected: Detect disagreement with the declared domain-specific reference and
reject the altered graph.
Negative: A visually plausible result is insufficient when operation order
violates the contract.
"""

from __future__ import annotations


CASE_ID = "TC-P050-04"
INTERVENTION = (
    "Move a reduction, blur, exposure scale, or color operation across an encoding "
    "boundary deliberately."
)
EXPECTED = (
    "Detect disagreement with the declared domain-specific reference and reject the "
    "altered graph."
)
NEGATIVE = (
    "A visually plausible result is insufficient when operation order violates the "
    "contract."
)

_DOMAINS = ("logarithmic", "display", "scene_linear")
_OPS = ("reduction", "blur", "exposure", "color")
_PAYLOAD_KEYS = ("domain", "operation", "crossed", "plausible", "reference")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "order_checked")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Reject an operation that crossed into an encoded domain."""
    domain, operation, crossed, plausible, reference = _payload(payload)
    preserved = [
        f"domain:{domain}",
        f"operation:{operation}",
        f"reference:{reference}",
        f"plausible:{str(plausible).lower()}",
    ]
    if crossed or domain != "scene_linear":
        rejected = ["order-violation"]
        reasons = [EXPECTED, "altered graph disagrees with the scene-linear reference"]
        if crossed:
            reasons.append(NEGATIVE)
        if plausible:
            reasons.append("visually plausible result rejected")
        if domain != "scene_linear":
            rejected.append("encoded-domain")
            reasons.append(f"domain:{domain} is not the declared scene-linear domain")
        return _result("rejected", reasons, rejected, preserved, ["graph was not repaired"])
    reasons = [
        EXPECTED,
        "operation stayed in the declared scene-linear domain",
        f"reference:{reference}",
    ]
    return _result("order_checked", reasons, [], preserved, [])


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    domain = payload["domain"]
    if domain not in _DOMAINS:
        raise ValueError("domain must be logarithmic, display, or scene_linear")
    operation = payload["operation"]
    if operation not in _OPS:
        raise ValueError("operation must be reduction, blur, exposure, or color")
    crossed = payload["crossed"]
    plausible = payload["plausible"]
    if type(crossed) is not bool or type(plausible) is not bool:
        raise ValueError("crossed and plausible must be bools")
    reference = payload["reference"]
    if not isinstance(reference, str) or not reference or reference != reference.strip():
        raise ValueError("reference must be a non-empty string")
    return domain, operation, crossed, plausible, reference


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("order decision cannot be qualified or allowed")
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
