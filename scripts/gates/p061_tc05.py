"""TC-P061-05 unconsented clipping.

Intervention: Supply encoded or intermediate values outside the selected
delivery domain without clipping permission.
Expected: Reject or request an explicit clipping policy and record affected
counts when clipping is authorized.
Negative: Silently clamping highlights while claiming full retained range must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P061-05"
INTERVENTION = (
    "Supply encoded or intermediate values outside the selected delivery domain without clipping permission."
)
EXPECTED = (
    "Reject or request an explicit clipping policy and record affected counts when clipping is authorized."
)
NEGATIVE = "Silently clamping highlights while claiming full retained range must fail."
REPEAT = "Repeat with negative channels, saturated colors, and extreme exposure adjustments."

_LOCI = ("negative-channel", "saturated", "extreme-exposure", "inside", "highlight")
_PAYLOAD_KEYS = (
    "value",
    "floor",
    "ceiling",
    "clippingPermitted",
    "claimFullRetainedRange",
    "affectedCount",
    "locus",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")


def evaluate(payload: dict) -> dict:
    """Refuse silent clamps. Authorized clips must record an affected count."""
    value, floor, ceiling, permitted, claim_full, affected, locus = _payload(payload)
    number = Decimal(value)
    low = Decimal(floor)
    high = Decimal(ceiling)
    outside = number < low or number > high
    preserved = [
        f"value:{value}",
        f"domain:{floor}..{ceiling}",
        f"locus:{locus}",
        f"affected:{affected}",
        f"clipping-permitted:{str(permitted).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"repeat coverage includes {REPEAT}"]
    rejected: list[str] = []
    questions: list[str] = []
    if claim_full and outside:
        rejected.append("silent-clamp-full-range")
        reasons.append(NEGATIVE)
    if outside and not permitted:
        rejected.append("unconsented-clip")
        reasons.append("value is outside the delivery domain without clipping permission")
        questions.append("explicit clipping policy required")
        decision = "rejected"
    elif outside and permitted and affected < 1:
        rejected.append("missing-affected-count")
        reasons.append("authorized clipping did not record an affected count")
        decision = "rejected"
    elif outside and permitted and claim_full:
        decision = "rejected"
        questions.append("full retained range cannot be claimed after clipping")
    elif outside and permitted:
        decision = "clip_recorded"
        reasons.append(f"clipping authorized; affected count {affected} recorded")
        questions.append("recorded clip is not a claim of full retained range")
    else:
        decision = "retained"
        reasons.append("value is inside the delivery domain")
        if affected != 0:
            raise ValueError("inside samples cannot carry a positive affected count")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    value = _decimal(payload["value"], "value")
    floor = _decimal(payload["floor"], "floor")
    ceiling = _decimal(payload["ceiling"], "ceiling")
    if Decimal(floor) >= Decimal(ceiling):
        raise ValueError("floor must be below ceiling")
    permitted = payload["clippingPermitted"]
    if type(permitted) is not bool:
        raise ValueError("clippingPermitted must be a bool")
    claim_full = payload["claimFullRetainedRange"]
    if type(claim_full) is not bool:
        raise ValueError("claimFullRetainedRange must be a bool")
    affected = payload["affectedCount"]
    if type(affected) is not int or isinstance(affected, bool) or affected < 0:
        raise ValueError("affectedCount must be a non-negative int")
    locus = payload["locus"]
    if locus not in _LOCI:
        raise ValueError("locus is unsupported")
    if not _locus_matches(locus, Decimal(value), Decimal(floor), Decimal(ceiling)):
        raise ValueError("value does not match locus")
    if Decimal(value) >= Decimal(floor) and Decimal(value) <= Decimal(ceiling) and affected != 0:
        raise ValueError("affectedCount must be 0 when the value is inside the domain")
    return value, floor, ceiling, permitted, claim_full, affected, locus


def _locus_matches(locus: str, value: Decimal, floor: Decimal, ceiling: Decimal) -> bool:
    if locus == "inside":
        return floor <= value <= ceiling
    if locus == "negative-channel":
        return value < 0
    if locus == "highlight":
        return value > ceiling
    if locus == "saturated":
        return value > ceiling
    if locus == "extreme-exposure":
        return value >= 8 or value <= -8
    return False


def _decimal(value: object, label: str) -> str:
    if not isinstance(value, str) or _SIGNED.fullmatch(value) is None or value == "-0":
        raise ValueError(label + " must be a canonical signed decimal")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P061-05 must not yield qualified or allowed")
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
