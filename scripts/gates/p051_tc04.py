"""TC-P051-04 nonlinear processing order.

Intervention: Move a reduction, blur, exposure scale, or color operation across
an encoding boundary deliberately.
Expected: Detect disagreement with the declared domain-specific reference and
reject the altered graph.
Negative: A visually plausible result is insufficient when operation order
violates the contract.
"""

from __future__ import annotations

from fractions import Fraction

CASE_ID = "TC-P051-04"
INTERVENTION = (
    "Move a reduction, blur, exposure scale, or color operation across an encoding boundary deliberately."
)
EXPECTED = (
    "Detect disagreement with the declared domain-specific reference and reject the altered graph."
)
NEGATIVE = "A visually plausible result is insufficient when operation order violates the contract."

_DOMAINS = ("scene-linear", "logarithmic", "display-encoded")
_OPERATIONS = ("exposure-scale", "blur", "reduction", "color")
_PLACEMENTS = ("before-encoding", "after-encoding")
_PAYLOAD_KEYS = (
    "domain",
    "operation",
    "declaredPlacement",
    "actualPlacement",
    "sample",
    "scale",
    "plausible",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "order_accepted")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Reject a graph that crosses the encoding boundary, even if it looks plausible."""
    domain, operation, declared, actual, sample, scale, plausible = _payload(payload)
    reference = _graph(domain, operation, declared, sample, scale)
    altered = _graph(domain, operation, actual, sample, scale)
    preserved = [
        f"domain:{domain}",
        f"operation:{operation}",
        f"sample:{sample}",
        f"scale:{scale}",
        f"reference:{_canon(reference)}",
        f"altered:{_canon(altered)}",
    ]
    if declared != actual:
        reasons = [
            EXPECTED,
            NEGATIVE,
            "altered graph rejected",
            f"reference {_canon(reference)} versus altered {_canon(altered)}",
        ]
        if plausible:
            reasons.append("visual plausibility does not accept the altered graph")
        return _result(
            "rejected",
            reasons,
            ["altered-operation-order"],
            preserved,
            ["operation order is not a visual judgement"],
        )
    return _result(
        "order_accepted",
        [EXPECTED, "declared domain order was left intact", f"reference {_canon(reference)}"],
        [],
        preserved,
        [],
    )


def _graph(domain: str, operation: str, placement: str, sample: int, scale: int) -> Fraction:
    if placement == "before-encoding":
        return _encode(domain, _apply(operation, Fraction(sample), Fraction(scale)))
    return _apply(operation, _encode(domain, Fraction(sample)), Fraction(scale))


def _apply(operation: str, value: Fraction, scale: Fraction) -> Fraction:
    if operation in {"exposure-scale", "color"}:
        return value * scale
    if operation == "reduction":
        return value / scale
    return value / 2


def _encode(domain: str, value: Fraction) -> Fraction:
    if domain == "scene-linear":
        return value
    if domain == "logarithmic":
        return Fraction(_log2_pow2(value))
    return value / (value + 1)


def _log2_pow2(value: Fraction) -> int:
    if value <= 0 or value.denominator != 1:
        raise ValueError("logarithmic operand must be a positive power of two")
    integer = value.numerator
    if integer & (integer - 1) != 0:
        raise ValueError("logarithmic operand must be a positive power of two")
    exponent = 0
    while integer > 1:
        integer //= 2
        exponent += 1
    return exponent


def _canon(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _pow2(value: object, label: str, limit: int) -> int:
    if type(value) is not int or value < 1 or value > limit or value & (value - 1) != 0:
        raise ValueError(label + " must be a positive power of two")
    return value


def _payload(payload: object) -> tuple[str, str, str, str, int, int, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    domain = payload["domain"]
    if domain not in _DOMAINS:
        raise ValueError("domain must be scene-linear, logarithmic, or display-encoded")
    operation = payload["operation"]
    if operation not in _OPERATIONS:
        raise ValueError("operation is not in the contract set")
    declared = payload["declaredPlacement"]
    actual = payload["actualPlacement"]
    if declared not in _PLACEMENTS or actual not in _PLACEMENTS:
        raise ValueError("placement must be before-encoding or after-encoding")
    sample = _pow2(payload["sample"], "sample", 65536)
    scale = _pow2(payload["scale"], "scale", 256)
    plausible = payload["plausible"]
    if type(plausible) is not bool:
        raise ValueError("plausible must be a bool")
    return domain, operation, declared, actual, sample, scale, plausible


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
