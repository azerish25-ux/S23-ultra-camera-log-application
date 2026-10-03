"""TC-P057-05 unconsented clipping.

Intervention: Supply encoded or intermediate values outside the selected
delivery domain without clipping permission.
Expected: Reject or request an explicit clipping policy and record affected
counts when clipping is authorized.
Negative: Silently clamping highlights while claiming full retained range must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P057-05"
INTERVENTION = (
    "Supply encoded or intermediate values outside the selected delivery domain "
    "without clipping permission."
)
EXPECTED = (
    "Reject or request an explicit clipping policy and record affected counts when "
    "clipping is authorized."
)
NEGATIVE = "Silently clamping highlights while claiming full retained range must fail."

_KINDS = ("negative-channel", "saturated-color", "extreme-exposure", "highlight")
_PAYLOAD_KEYS = (
    "kind",
    "value",
    "domainMin",
    "domainMax",
    "clippingPermitted",
    "silentClamp",
    "claimsFullRange",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld", "clip_recorded")
_FORBIDDEN = {"qualified", "allowed"}
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")


def evaluate(payload: dict) -> dict:
    """Reject silent clamps. Record a count only when clipping is explicit."""
    kind, value, low, high, permitted, silent, full_range = _payload(payload)
    outside = value < low or value > high
    preserved = [
        f"kind:{kind}",
        f"value:{_text(value)}",
        f"domain:{_text(low)}..{_text(high)}",
        f"clipping-permitted:{str(permitted).lower()}",
        f"silent-clamp:{str(silent).lower()}",
        f"claims-full-range:{str(full_range).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = ["clipping policy is not a physical S23 qualification"]
    if silent and full_range:
        reasons.append(NEGATIVE)
        preserved.append("affected:hidden")
        questions.append("silent clamp cannot claim the original range")
        return _result("rejected", reasons, ["silent-clamp-full-range"], preserved, questions)
    if outside and not permitted:
        reasons.append("value is outside the delivery domain without clipping permission")
        preserved.append("affected:unrecorded")
        questions.append("explicit clipping policy required")
        return _result("rejected", reasons, ["unconsented-clip"], preserved, questions)
    if outside and permitted:
        reasons.append("authorized clip recorded an affected count")
        preserved.append("affected:1")
        preserved.append(f"clamped-to:{_text(min(high, max(low, value)))}")
        return _result("clip_recorded", reasons, [], preserved, questions)
    reasons.append("in-range value was kept without a clip")
    preserved.append("affected:0")
    return _result("withheld", reasons, [], preserved, questions)


def _text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _payload(payload: object) -> tuple[str, Decimal, Decimal, Decimal, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    kind = payload["kind"]
    if kind not in _KINDS:
        raise ValueError("kind is unknown")
    numbers = []
    for name in ("value", "domainMin", "domainMax"):
        text = payload[name]
        if not isinstance(text, str) or _DECIMAL.fullmatch(text) is None:
            raise ValueError(name + " must be a canonical decimal string")
        numbers.append(Decimal(text))
    value, low, high = numbers
    if low >= high:
        raise ValueError("domainMax must exceed domainMin")
    flags = []
    for name in ("clippingPermitted", "silentClamp", "claimsFullRange"):
        flag = payload[name]
        if type(flag) is not bool:
            raise ValueError(name + " must be a bool")
        flags.append(flag)
    return (kind, value, low, high, *flags)


def _result(decision, reasons, rejected, preserved, questions) -> dict:
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
